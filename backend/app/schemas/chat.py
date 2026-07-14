from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ChatMessageIn(BaseModel):
    session_id: str | None = None  # None -> a new session is created
    rep_id: str
    text: str


class ToolActionOut(BaseModel):
    tool: str
    status: str  # "ok" | "needs_clarification" | "flagged" | "error"
    data: dict = {}


class ChatMessageOut(BaseModel):
    session_id: str
    reply: str
    tool_actions: list[ToolActionOut] = []


class ChatMessageRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    tool_calls: dict
    created_at: datetime


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rep_id: str
    hcp_id: str | None
    started_at: datetime
    messages: list[ChatMessageRecord] = []
