from pydantic import BaseModel, ConfigDict


class HCPBase(BaseModel):
    name: str
    specialty: str | None = None
    institution: str | None = None
    territory: str | None = None
    contact_info: dict = {}


class HCPCreate(HCPBase):
    pass


class HCPOut(HCPBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    compliance_flags: dict = {}


class HCPSearchResult(HCPOut):
    last_interaction_date: str | None = None
    interaction_count: int = 0
