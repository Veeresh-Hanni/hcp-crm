from sqlalchemy.orm import Session

from app.agent.llm_client import fast_llm, call_json
from app.services import hcp_service
from app.services import interaction_service

LOOKUP_PROMPT = """Extract the HCP name from this CRM lookup question.

Return JSON:
{"hcp_name": string or null}
"""


def lookup_hcp(db: Session, name_query: str) -> dict:
    """
    Tool #3. Fuzzy-searches HCPs by name and returns context.
    """
    extracted = call_json(fast_llm(), LOOKUP_PROMPT, name_query)
    query = extracted.get("hcp_name") or name_query
    candidates = hcp_service.search_hcps(db, query, limit=5)
    if not candidates:
        return {"status": "not_found", "message": f"No HCPs found matching '{query}'."}

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