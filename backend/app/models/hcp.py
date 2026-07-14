import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class HCP(Base):
    __tablename__ = "hcps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    specialty: Mapped[str] = mapped_column(String(255), nullable=True)
    institution: Mapped[str] = mapped_column(String(255), nullable=True)
    territory: Mapped[str] = mapped_column(String(255), nullable=True)
    contact_info: Mapped[dict] = mapped_column(JSON, default=dict)
    compliance_flags: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="hcp")
