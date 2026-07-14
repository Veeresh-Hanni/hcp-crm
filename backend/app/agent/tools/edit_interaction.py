from sqlalchemy.orm import Session

from app.agent.llm_client import fast_llm, call_json
from app.services import interaction_service

DIFF_PROMPT = """You are helping edit a previously logged HCP interaction record.

Current record (JSON): {current}

The rep just said what they want changed. Return JSON describing ONLY the fields to change:
{{
  "sentiment": "positive" | "neutral" | "negative" (optional),
  "discussion_notes": string (optional),
  "next_steps": string (optional),
  "summary": string (optional),
  "interaction_date": "YYYY-MM-DD" (optional)
}}

Only include keys that should actually change based on the rep's instruction. Omit anything unchanged.
"""


def edit_interaction(db: Session, rep_id: str, raw_text: str, interaction_id: str | None, last_interaction_id: str | None) -> dict:
    """
    Mandatory tool #2.

    Resolves which interaction to edit (explicit id, or falls back to the
    most recently logged one in this session), asks the LLM to turn the
    rep's natural-language correction into a structured field diff, applies
    it via the shared service layer (which also writes audit_log rows),
    and returns the updated record.
    """
    target_id = interaction_id or last_interaction_id
    if not target_id:
        return {"status": "needs_clarification", "question": "Which interaction would you like to edit? I don't have a recent one in this session."}

    current = interaction_service.get_interaction(db, target_id)
    if not current:
        return {"status": "error", "message": f"No interaction found with id {target_id}."}

    current_snapshot = {
        "sentiment": current.sentiment,
        "discussion_notes": current.discussion_notes,
        "next_steps": current.next_steps,
        "summary": current.summary,
        "interaction_date": current.interaction_date.isoformat(),
    }

    diff = call_json(fast_llm(), DIFF_PROMPT.format(current=current_snapshot), raw_text)

    if "interaction_date" in diff:
        from datetime import datetime
        diff["interaction_date"] = datetime.fromisoformat(diff["interaction_date"])

    if not diff:
        return {"status": "needs_clarification", "question": "I couldn't tell what you'd like changed — could you be more specific?"}

    updated = interaction_service.update_interaction(db, target_id, diff, changed_by=rep_id)

    return {
        "status": "ok",
        "interaction": {
            "id": updated.id,
            "changed_fields": list(diff.keys()),
            "sentiment": updated.sentiment,
            "discussion_notes": updated.discussion_notes,
            "next_steps": updated.next_steps,
            "summary": updated.summary,
        },
    }
