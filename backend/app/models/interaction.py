import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Text, ForeignKey, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class InteractionType(str, enum.Enum):
    visit = "visit"
    call = "call"
    email = "email"
    virtual = "virtual"


class Sentiment(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class Source(str, enum.Enum):
    form = "form"
    chat = "chat"


class ComplianceStatus(str, enum.Enum):
    clear = "clear"
    flagged = "flagged"
    unreviewed = "unreviewed"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    approved_claims: Mapped[dict] = mapped_column(JSON, default=dict)


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hcp_id: Mapped[str] = mapped_column(String(36), ForeignKey("hcps.id"), nullable=False)
    rep_id: Mapped[str] = mapped_column(String(36), nullable=False)

    interaction_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    type: Mapped[InteractionType] = mapped_column(Enum(InteractionType), nullable=False)

    summary: Mapped[str] = mapped_column(Text, nullable=True)
    discussion_notes: Mapped[str] = mapped_column(Text, nullable=True)
    sentiment: Mapped[Sentiment] = mapped_column(Enum(Sentiment), nullable=True)

    materials_shared: Mapped[dict] = mapped_column(JSON, default=dict)
    samples_given: Mapped[dict] = mapped_column(JSON, default=dict)
    next_steps: Mapped[str] = mapped_column(Text, nullable=True)

    source: Mapped[Source] = mapped_column(Enum(Source), default=Source.form)
    compliance_status: Mapped[ComplianceStatus] = mapped_column(
        Enum(ComplianceStatus), default=ComplianceStatus.unreviewed
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")
    products = relationship("InteractionProduct", back_populates="interaction", cascade="all, delete-orphan")


class InteractionProduct(Base):
    __tablename__ = "interaction_products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    interaction_id: Mapped[str] = mapped_column(String(36), ForeignKey("interactions.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), nullable=False)
    discussion_notes: Mapped[str] = mapped_column(Text, nullable=True)

    interaction = relationship("Interaction", back_populates="products")
    product = relationship("Product")
