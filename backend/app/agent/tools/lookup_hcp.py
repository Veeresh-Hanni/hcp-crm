import re

from sqlalchemy.orm import Session

from app.agent.llm_client import fast_llm, call_json
from app.models import HCP
from app.services import hcp_service
from app.services import interaction_service

LOOKUP_PROMPT = """Extract the HCP name from this CRM lookup question.

Return JSON:
{"hcp_name": string or null}
"""


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _extract_dr_name(text: str) -> str | None:
    match = re.search(r"\bDr\.?\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)", text, flags=re.IGNORECASE)
    if not match:
        return None
    parts = " ".join(match.group(1).split()).title()
    return f"Dr. {parts}"


def lookup_hcp(db: Session, name_query: str) -> dict:
    """
    Tool #3. Fuzzy-searches HCPs by name and returns context.
    """
    extracted_name = _extract_dr_name(name_query)
    if not extracted_name:
        extracted = call_json(fast_llm(), LOOKUP_PROMPT, name_query)
        extracted_name = extracted.get("hcp_name")

    query = extracted_name or name_query
    candidates = hcp_service.search_hcps(db, query, limit=5)
    if not candidates:
        return {"status": "not_found", "message": f"No HCPs found matching '{query}'."}

    exact_hcp = (
        db.query(HCP)
        .all()
    )
    exact_match = next((hcp for hcp in exact_hcp if _normalize_name(hcp.name) == _normalize_name(query)), None)
    if exact_match:
        exact_candidate = next((candidate for candidate in candidates if candidate["id"] == exact_match.id), None)
        if exact_candidate:
            candidates = [exact_candidate] + [candidate for candidate in candidates if candidate["id"] != exact_match.id]

    top = candidates[0]
    latest = interaction_service.list_interactions_for_hcp(db, top["id"], limit=1)
    interaction = latest[0] if latest else None
    
    # Safely look for any possible text field inside the raw database record object
    raw_notes = ""
    if interaction:
        raw_notes = (
            getattr(interaction, "summary", None) or 
            getattr(interaction, "discussion_notes", None) or 
            getattr(interaction, "notes", None) or 
            ""
        )

    return {
        "status": "ok",
        "candidates": candidates,
        "interaction": {
            "id": interaction.id,
            "hcp_id": top["id"],
            "hcp_name": top["name"],
            "interaction_date": interaction.interaction_date.isoformat(),
            "type": interaction.type.value if hasattr(interaction.type, "value") else interaction.type,
            "summary": raw_notes,  # Guaranteed parsed text string
            "materials_shared": interaction.materials_shared,
            "samples_given": interaction.samples_given,
            "sentiment": interaction.sentiment.value if hasattr(interaction.sentiment, "value") else interaction.sentiment,
            "next_steps": interaction.next_steps,
        } if interaction else None,
    }
