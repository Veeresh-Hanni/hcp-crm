from sqlalchemy.orm import Session

from app.agent.llm_client import reasoning_llm, call_json
from app.models import Interaction, ComplianceStatus

# Simple configurable rule: max sample units per HCP per quarter.
MAX_SAMPLES_PER_QUARTER = 10

COMPLIANCE_PROMPT = """You are a pharmaceutical compliance reviewer. Scan these discussion notes from a rep's
HCP interaction for potential off-label claims or promises that exceed approved product claims
(efficacy claims not backed by label, guarantees of outcomes, comparative claims against competitors
without data, etc).

Discussion notes: {notes}

Return JSON:
{{
  "risk_detected": true | false,
  "reasons": [list of strings, empty if risk_detected is false]
}}
"""


def compliance_check(db: Session, interaction_id: str) -> dict:
    """
    Tool #5. Runs both a deterministic rule check (sample quantity limits)
    and an LLM scan of discussion notes for off-label/unsupported claims
    language. Flags rather than blocks — the interaction stays logged,
    but compliance_status is updated for review queues.
    """
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        return {"status": "error", "message": f"No interaction found with id {interaction_id}."}

    reasons = []

    total_samples = sum(interaction.samples_given.values()) if interaction.samples_given else 0
    if total_samples > MAX_SAMPLES_PER_QUARTER:
        reasons.append(f"Sample quantity ({total_samples}) exceeds per-interaction guidance ({MAX_SAMPLES_PER_QUARTER}).")

    if interaction.discussion_notes:
        llm_result = call_json(reasoning_llm(), COMPLIANCE_PROMPT.format(notes=interaction.discussion_notes), "Review now.")
        if llm_result.get("risk_detected"):
            reasons.extend(llm_result.get("reasons", []))

    interaction.compliance_status = ComplianceStatus.flagged if reasons else ComplianceStatus.clear
    db.commit()

    return {
        "status": "flagged" if reasons else "clear",
        "reasons": reasons,
        "interaction_id": interaction_id,
    }
