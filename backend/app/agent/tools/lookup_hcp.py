from sqlalchemy.orm import Session

from app.services import hcp_service


def lookup_hcp(db: Session, name_query: str) -> dict:
    """
    Tool #3. Fuzzy-searches HCPs by name and returns context (specialty,
    last interaction, interaction frequency, compliance flags) so the rep
    can be given info directly, or so the agent can disambiguate an
    ambiguous name before logging/editing.
    """
    candidates = hcp_service.search_hcps(db, name_query, limit=5)
    if not candidates:
        return {"status": "not_found", "message": f"No HCPs found matching '{name_query}'."}
    return {"status": "ok", "candidates": candidates}
