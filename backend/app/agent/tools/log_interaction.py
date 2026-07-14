from datetime import datetime

from sqlalchemy.orm import Session

from app.agent.llm_client import fast_llm, call_json
from app.services import hcp_service, interaction_service

EXTRACTION_PROMPT = """You are an assistant that extracts structured HCP (Healthcare Professional) interaction
data from a pharma field rep's free-text description of a visit, call, email, or virtual meeting.

Extract these fields as JSON:
{
  "hcp_name": string or null,
  "interaction_date": "YYYY-MM-DD" or null (assume today if the text implies "today"/"this morning" etc, otherwise null),
  "type": one of "visit" | "call" | "email" | "virtual" or null,
  "products": [list of product names mentioned],
  "materials_shared": {"item": "description"} or {},
  "samples_given": {"product_name": quantity} or {},
  "sentiment": one of "positive" | "neutral" | "negative" or null,
  "discussion_notes": a factual, complete restatement of what was discussed,
  "next_steps": string or null
}

Today's date is __TODAY__. Only include information actually present in the text — use null rather than guessing.
"""

SUMMARY_PROMPT = """Write a single, concise 1-2 sentence professional summary of this HCP interaction,
suitable for a CRM list view. Return JSON: {"summary": "..."}"""


def log_interaction(db: Session, rep_id: str, raw_text: str, draft: dict | None = None) -> dict:
    """
    Mandatory tool #1.

    Extracts structured interaction data from free text using gemma2-9b-it,
    resolves the HCP via fuzzy match, generates a short LLM summary, validates
    required fields, and — only if everything required is present — writes the
    interaction via the shared service layer (same path the form UI uses).

    Returns a dict with a `status` of:
      - "needs_clarification": missing/ambiguous field, includes `question`
      - "ok": interaction created, includes `interaction`
    """
    draft = draft or {}
    today = datetime.utcnow().strftime("%Y-%m-%d")

    extracted = call_json(fast_llm(), EXTRACTION_PROMPT.replace("__TODAY__", today), raw_text)
    # merge extracted fields over any prior draft (later turns refine earlier ones)
    merged = {**draft, **{k: v for k, v in extracted.items() if v not in (None, [], {})}}

    hcp_name = merged.get("hcp_name")
    if not hcp_name:
        return {"status": "needs_clarification", "question": "Which HCP was this interaction with?", "draft": merged}

    hcp, candidates = hcp_service.resolve_single_hcp(db, hcp_name)
    if hcp is None:
        if len(candidates) > 1:
            names = ", ".join(c["name"] for c in candidates[:3])
            return {
                "status": "needs_clarification",
                "question": f"I found multiple HCPs matching '{hcp_name}': {names}. Which one did you mean?",
                "draft": merged,
                "candidates": candidates,
            }
        return {
            "status": "needs_clarification",
            "question": f"I couldn't find an HCP named '{hcp_name}' in the system. Could you confirm the spelling, or add them first?",
            "draft": merged,
        }

    if not merged.get("interaction_date"):
        return {"status": "needs_clarification", "question": "What date did this interaction happen?", "draft": merged}

    if not merged.get("type"):
        return {"status": "needs_clarification", "question": "Was this a visit, call, email, or virtual meeting?", "draft": merged}

    summary_result = call_json(fast_llm(), SUMMARY_PROMPT, merged.get("discussion_notes") or raw_text)

    payload = {
        "hcp_id": hcp.id,
        "interaction_date": datetime.fromisoformat(merged["interaction_date"]),
        "type": merged["type"],
        "summary": summary_result.get("summary"),
        "discussion_notes": merged.get("discussion_notes"),
        "sentiment": merged.get("sentiment"),
        "materials_shared": merged.get("materials_shared", {}),
        "samples_given": merged.get("samples_given", {}),
        "next_steps": merged.get("next_steps"),
        "product_names": merged.get("products", []),
    }

    interaction = interaction_service.create_interaction(db, payload, rep_id=rep_id, source="chat")

    return {
        "status": "ok",
        "interaction": {
            "id": interaction.id,
            "hcp_name": hcp.name,
            "interaction_date": interaction.interaction_date.isoformat(),
            "type": interaction.type,
            "summary": interaction.summary,
            "sentiment": interaction.sentiment,
            "next_steps": interaction.next_steps,
        },
    }