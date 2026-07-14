from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Interaction, InteractionProduct, Product, AuditLog, ComplianceStatus


REQUIRED_FIELDS = ["hcp_id", "interaction_date", "type"]


def validate_interaction_payload(payload: dict) -> list[str]:
    """Returns a list of missing/invalid required fields. Empty list = valid."""
    missing = [f for f in REQUIRED_FIELDS if not payload.get(f)]
    return missing


def get_or_create_product(db: Session, name: str) -> Product:
    product = db.query(Product).filter(Product.name.ilike(name)).first()
    if product:
        return product
    product = Product(name=name)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def create_interaction(db: Session, payload: dict, rep_id: str, source: str = "form") -> Interaction:
    """
    Single write path for a new interaction. Both the POST /interactions route
    and the log_interaction agent tool call this, so validation and
    product-linking behavior is guaranteed identical regardless of entry mode.
    """
    missing = validate_interaction_payload(payload)
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    product_names = payload.pop("product_names", [])

    interaction = Interaction(
        hcp_id=payload["hcp_id"],
        rep_id=rep_id,
        interaction_date=payload["interaction_date"],
        type=payload["type"],
        summary=payload.get("summary"),
        discussion_notes=payload.get("discussion_notes"),
        sentiment=payload.get("sentiment"),
        materials_shared=payload.get("materials_shared", {}),
        samples_given=payload.get("samples_given", {}),
        next_steps=payload.get("next_steps"),
        source=source,
        compliance_status=ComplianceStatus.unreviewed,
    )
    db.add(interaction)
    db.flush()  # get interaction.id before linking products

    for name in product_names:
        product = get_or_create_product(db, name)
        db.add(InteractionProduct(interaction_id=interaction.id, product_id=product.id))

    db.commit()
    db.refresh(interaction)
    return interaction


def update_interaction(db: Session, interaction_id: str, changes: dict, changed_by: str) -> Interaction | None:
    """
    Applies a partial update and writes one audit_log row per changed field.
    Used by both PATCH /interactions/{id} and the edit_interaction agent tool.
    """
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        return None

    for field, new_value in changes.items():
        if field == "changed_by" or new_value is None:
            continue
        old_value = getattr(interaction, field, None)
        if str(old_value) == str(new_value):
            continue
        db.add(
            AuditLog(
                interaction_id=interaction.id,
                field=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value),
                changed_by=changed_by,
                changed_at=datetime.utcnow(),
            )
        )
        setattr(interaction, field, new_value)

    interaction.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(interaction)
    return interaction


def get_interaction(db: Session, interaction_id: str) -> Interaction | None:
    return db.query(Interaction).filter(Interaction.id == interaction_id).first()


def list_interactions_for_hcp(db: Session, hcp_id: str, limit: int = 20) -> list[Interaction]:
    return (
        db.query(Interaction)
        .filter(Interaction.hcp_id == hcp_id)
        .order_by(Interaction.interaction_date.desc(), Interaction.created_at.desc())
        .limit(limit)
        .all()
    )
