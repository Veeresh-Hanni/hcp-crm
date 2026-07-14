from sqlalchemy.orm import Session

from app.agent.llm_client import fast_llm, call_json
from app.agent.state import AgentState
from app.agent import tools as agent_tools
from app.services import interaction_service

ROUTER_PROMPT = """You are the intent router for a pharma field-rep CRM chat assistant. Classify the rep's
message into exactly one intent:

- "log": recounting/describing an HCP interaction that should be logged (a visit, call, email, meeting)
- "edit": asking to change/correct/update a previously logged interaction
- "lookup": asking about an HCP (who they are, when last visited, etc) without describing a new interaction
- "suggest": asking what to discuss next / for prep advice for an upcoming HCP visit
- "compliance": explicitly asking to check compliance on a logged interaction
- "chitchat": greeting, thanks, or anything not covered above

Return JSON: {"intent": "..."}
"""


def router_node(state: AgentState, db: Session) -> AgentState:
    result = call_json(fast_llm(), ROUTER_PROMPT, state["user_text"])
    state["intent"] = result.get("intent", "chitchat")
    return state


def log_node(state: AgentState, db: Session) -> AgentState:
    result = agent_tools.log_interaction(
        db, rep_id=state["rep_id"], raw_text=state["user_text"], draft=state.get("draft_interaction", {})
    )
    state["tool_result"] = {"tool": "log_interaction", **result}
    if result["status"] == "needs_clarification":
        state["needs_clarification"] = True
        state["draft_interaction"] = result.get("draft", {})
        state["reply"] = result["question"]
    else:
        state["needs_clarification"] = False
        state["draft_interaction"] = {}
        state["last_interaction_id"] = result["interaction"]["id"]
        state["active_hcp_id"] = result["interaction"].get("hcp_id")
        i = result["interaction"]
        state["reply"] = (
            f"Logged: {i['hcp_name']} — {i['type']} on {i['interaction_date'][:10]}. "
            f"Summary: {i['summary']}"
            + (f" Next steps: {i['next_steps']}." if i.get("next_steps") else "")
        )
    return state


def edit_node(state: AgentState, db: Session) -> AgentState:
    result = agent_tools.edit_interaction(
        db,
        rep_id=state["rep_id"],
        raw_text=state["user_text"],
        interaction_id=None,
        last_interaction_id=state.get("last_interaction_id"),
    )
    state["tool_result"] = {"tool": "edit_interaction", **result}
    if result["status"] == "needs_clarification":
        state["needs_clarification"] = True
        state["reply"] = result["question"]
    elif result["status"] == "error":
        state["needs_clarification"] = False
        state["reply"] = result["message"]
    else:
        state["needs_clarification"] = False
        state["active_hcp_id"] = result["interaction"].get("hcp_id")
        state["last_interaction_id"] = result["interaction"]["id"]
        fields = ", ".join(result["interaction"]["changed_fields"])
        state["reply"] = f"Updated {fields} on that interaction."
    return state


def lookup_node(state: AgentState, db: Session) -> AgentState:
    result = agent_tools.lookup_hcp(db, name_query=state["user_text"])
    state["tool_result"] = {"tool": "lookup_hcp", **result}
    
    if result["status"] == "not_found":
        state["reply"] = result["message"]
    else:
        top = result["candidates"][0]
        state["active_hcp_id"] = top["id"]
        
        if result.get("interaction"):
            state["last_interaction_id"] = result["interaction"]["id"]
            latest = result["interaction"]

            summary_text = latest.get("discussion_notes") or latest.get("summary") or "No notes captured"
            date_str = latest.get("interaction_date", "")
            sentiment = latest.get("sentiment") or "n/a"

            clean_date = date_str[:10] if date_str else "n/a"

            state["reply"] = (
                f"{top['name']} ({top.get('specialty') or 'specialty n/a'}) — "
                f"latest interaction on {clean_date}: {summary_text.rstrip('.')}. "
                f"Sentiment: {sentiment}. "
                f"{top.get('interaction_count', 0)} total interactions."
            )
        else:
            state["reply"] = (
                f"{top['name']} ({top.get('specialty') or 'specialty n/a'}) — "
                f"no interactions logged yet. {top.get('interaction_count', 0)} total interactions."
            )
            
    state["needs_clarification"] = False
    return state



    
def suggest_node(state: AgentState, db: Session) -> AgentState:
    hcp_id = state.get("active_hcp_id")
    if not hcp_id:
        lookup = agent_tools.lookup_hcp(db, name_query=state["user_text"])
        if lookup.get("status") == "ok" and lookup.get("candidates"):
            hcp_id = lookup["candidates"][0]["id"]
            state["active_hcp_id"] = hcp_id
            if lookup.get("interaction"):
                state["last_interaction_id"] = lookup["interaction"]["id"]
        else:
            state["reply"] = "Which HCP would you like a suggestion for?"
            state["needs_clarification"] = True
            return state
    result = agent_tools.suggest_next_best_action(db, hcp_id=hcp_id)
    state["tool_result"] = {"tool": "suggest_next_best_action", **result}
    state["needs_clarification"] = False
    if result["status"] == "no_history":
        state["reply"] = result["message"]
    else:
        state["reply"] = (
            f"Suggested next talking point: {result['recommended_talking_point']} "
            f"({result['reasoning']}) Follow up {result['suggested_follow_up_timing']}."
        )
    return state


def compliance_node(state: AgentState, db: Session) -> AgentState:
    interaction_id = state.get("last_interaction_id")
    if not interaction_id and state.get("active_hcp_id"):
        latest = interaction_service.list_interactions_for_hcp(db, state["active_hcp_id"], limit=1)
        if latest:
            interaction_id = latest[0].id
            state["last_interaction_id"] = interaction_id

    if not interaction_id:
        state["reply"] = "I don't have a recent interaction in this session to compliance-check."
        state["needs_clarification"] = True
        return state
    result = agent_tools.compliance_check(db, interaction_id=interaction_id)
    state["tool_result"] = {"tool": "compliance_check", **result}
    state["needs_clarification"] = False
    if result["status"] == "flagged":
        state["reply"] = "⚠️ Compliance review flagged this interaction: " + "; ".join(result["reasons"])
    else:
        state["reply"] = "✅ No compliance concerns found."
    return state


def chitchat_node(state: AgentState, db: Session) -> AgentState:
    state["reply"] = "I'm here to help you log or manage HCP interactions — tell me about a visit or call, or ask about an HCP."
    state["needs_clarification"] = False
    state["tool_result"] = {}
    return state
