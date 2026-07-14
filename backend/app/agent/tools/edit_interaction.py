import re

from sqlalchemy.orm import Session

from app.agent.llm_client import fast_llm, call_json
from app.models import HCP
from app.services import hcp_service, interaction_service

DIFF_PROMPT = """You are helping edit a previously logged HCP interaction record.

Current record (JSON): {current}

The rep just said what they want changed. Return JSON describing ONLY the fields to change:
{{
  "sentiment": "positive" | "neutral" | "negative" (optional),
  "hcp_name": string (optional),
  "discussion_notes": string (optional),
  "next_steps": string (optional),
  "summary": string (optional),
  "interaction_date": "YYYY-MM-DD" (optional)
}}

Only include keys that should actually change based on the rep's instruction. Omit anything unchanged.
"""


def _extract_dr_name(text: str) -> str | None:
    match = re.search(r"\bDr\.?\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)", text, flags=re.IGNORECASE)
    if not match:
        return None
    return f"Dr. {' '.join(match.group(1).split()).title()}"


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
        "hcp_name": current.hcp.name if current.hcp else None,
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

    changed_hcp_name = _extract_dr_name(raw_text) or diff.pop("hcp_name", None)
    if "hcp_name" in diff:
        diff.pop("hcp_name", None)
    if changed_hcp_name:
        hcp, candidates = hcp_service.resolve_single_hcp(db, changed_hcp_name)
        if hcp is None and len(candidates) > 1:
            names = ", ".join(c["name"] for c in candidates[:3])
            return {
                "status": "needs_clarification",
                "question": f"I found multiple HCPs matching '{changed_hcp_name}': {names}. Which one did you mean?",
            }
        if hcp is None:
            hcp = hcp_service.create_hcp(db, {"name": changed_hcp_name, "contact_info": {}})
        diff["hcp_id"] = hcp.id

    if not diff:
        return {"status": "needs_clarification", "question": "I couldn't tell what you'd like changed — could you be more specific?"}

    updated = interaction_service.update_interaction(db, target_id, diff, changed_by=rep_id)
    updated_hcp = db.query(HCP).filter(HCP.id == updated.hcp_id).first()
    changed_fields = ["hcp_name" if field == "hcp_id" else field for field in diff.keys()]

    return {
        "status": "ok",
        "interaction": {
            "id": updated.id,
            "hcp_id": updated.hcp_id,
            "hcp_name": updated_hcp.name if updated_hcp else None,
            "changed_fields": changed_fields,
            "interaction_date": updated.interaction_date.isoformat(),
            "type": updated.type.value if hasattr(updated.type, "value") else updated.type,
            "sentiment": updated.sentiment.value if hasattr(updated.sentiment, "value") else updated.sentiment,
            "discussion_notes": updated.discussion_notes,
            "materials_shared": updated.materials_shared,
            "samples_given": updated.samples_given,
            "next_steps": updated.next_steps,
            "summary": updated.summary,
        },
    }
