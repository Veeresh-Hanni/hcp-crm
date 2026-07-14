from rapidfuzz import fuzz, process
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import HCP, Interaction


def search_hcps(db: Session, query: str, limit: int = 5) -> list[dict]:
    """
    Fuzzy name search. Returns HCPs ranked by name similarity, each annotated
    with last interaction date + interaction count, so both the UI autocomplete
    and the lookup_hcp agent tool get the same context.
    """
    all_hcps = db.query(HCP).all()
    if not all_hcps:
        return []

    choices = {h.id: h.name for h in all_hcps}
    matches = process.extract(query, choices, scorer=fuzz.WRatio, limit=limit)
    # matches: list of (name, score, hcp_id)

    results = []
    for name, score, hcp_id in matches:
        if score < 50:  # cutoff to avoid nonsense matches
            continue
        hcp = next(h for h in all_hcps if h.id == hcp_id)
        last = (
            db.query(Interaction)
            .filter(Interaction.hcp_id == hcp_id)
            .order_by(Interaction.interaction_date.desc())
            .first()
        )
        count = db.query(func.count(Interaction.id)).filter(Interaction.hcp_id == hcp_id).scalar()
        results.append(
            {
                "id": hcp.id,
                "name": hcp.name,
                "specialty": hcp.specialty,
                "institution": hcp.institution,
                "territory": hcp.territory,
                "compliance_flags": hcp.compliance_flags,
                "match_score": score,
                "last_interaction_date": last.interaction_date.isoformat() if last else None,
                "interaction_count": count,
            }
        )
    return results


def resolve_single_hcp(db: Session, name_guess: str) -> tuple[HCP | None, list[dict]]:
    """
    Used by log_interaction: tries to resolve a name to exactly one HCP.
    Returns (hcp, candidates). If hcp is None and candidates has >1 entries,
    the caller should treat this as ambiguous and ask the user to disambiguate.
    """
    candidates = search_hcps(db, name_guess, limit=5)
    if not candidates:
        return None, []
    if len(candidates) == 1 or candidates[0]["match_score"] >= 90:
        hcp = db.query(HCP).filter(HCP.id == candidates[0]["id"]).first()
        return hcp, candidates
    return None, candidates


def create_hcp(db: Session, data: dict) -> HCP:
    hcp = HCP(**data)
    db.add(hcp)
    db.commit()
    db.refresh(hcp)
    return hcp
