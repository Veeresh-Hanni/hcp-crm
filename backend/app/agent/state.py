from typing import TypedDict, Literal


class AgentState(TypedDict, total=False):
    session_id: str
    rep_id: str
    user_text: str

    intent: Literal["log", "edit", "lookup", "suggest", "compliance", "chitchat"]
    active_hcp_id: str | None
    draft_interaction: dict
    last_interaction_id: str | None

    tool_result: dict
    reply: str
    needs_clarification: bool
