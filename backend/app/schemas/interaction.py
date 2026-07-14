from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.interaction import InteractionType, Sentiment, Source, ComplianceStatus


class InteractionBase(BaseModel):
    hcp_id: str
    interaction_date: datetime
    type: InteractionType
    summary: str | None = None
    discussion_notes: str | None = None
    sentiment: Sentiment | None = None
    materials_shared: dict = {}
    samples_given: dict = {}
    next_steps: str | None = None
    product_names: list[str] = []  # simple list for form mode; resolved to Product rows server-side


class InteractionCreate(InteractionBase):
    source: Source = Source.form


class InteractionUpdate(BaseModel):
    interaction_date: datetime | None = None
    type: InteractionType | None = None
    summary: str | None = None
    discussion_notes: str | None = None
    sentiment: Sentiment | None = None
    materials_shared: dict | None = None
    samples_given: dict | None = None
    next_steps: str | None = None
    changed_by: str  # rep_id making the edit, required for audit log


class InteractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    hcp_id: str
    rep_id: str
    interaction_date: datetime
    type: InteractionType
    summary: str | None
    discussion_notes: str | None
    sentiment: Sentiment | None
    materials_shared: dict
    samples_given: dict
    next_steps: str | None
    source: Source
    compliance_status: ComplianceStatus
    created_at: datetime
    updated_at: datetime
