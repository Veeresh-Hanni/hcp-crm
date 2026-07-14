from sqlalchemy.orm import Session

from app.agent.llm_client import reasoning_llm, call_json
from app.services import interaction_service, hcp_service

SUGGEST_PROMPT = """You are a life-sciences sales enablement assistant. Given an HCP's recent interaction
history, recommend the single best next talking point and ideal follow-up timing for the rep's next visit.

Recent interactions (JSON, most recent first): {history}

Consider: sentiment trend, products already discussed vs. not yet covered, and how recently they last spoke.

Return JSON:
{{
  "recommended_talking_point": string,
  "reasoning": string (1-2 sentences),
  "suggested_follow_up_timing": string (e.g. "within 1 week", "next quarter")
}}
"""


def suggest_next_best_action(db: Session, hcp_id: str) -> dict:
    """
    Tool #4 (sales enablement). Uses the heavier-reasoning model
    (llama-3.3-70b-versatile) since synthesizing a recommendation across
    history benefits more from reasoning depth than raw speed.
    """
    history = interaction_service.list_interactions_for_hcp(db, hcp_id, limit=5)
    if not history:
        return {"status": "no_history", "message": "No prior interactions logged for this HCP yet."}

    history_json = [
        {
            "date": h.interaction_date.isoformat(),
            "type": h.type,
            "summary": h.summary,
            "sentiment": h.sentiment,
        }
        for h in history
    ]

    result = call_json(reasoning_llm(), SUGGEST_PROMPT.format(history=history_json), "Generate the recommendation now.")
    return {"status": "ok", **result}
