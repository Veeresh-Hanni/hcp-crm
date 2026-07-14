from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.interaction import InteractionCreate, InteractionUpdate, InteractionOut
from app.services import interaction_service

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.post("/", response_model=InteractionOut)
def create_interaction(payload: InteractionCreate, rep_id: str, db: Session = Depends(get_db)):
    """Form-mode create. rep_id passed as query param until auth is wired up."""
    try:
        data = payload.model_dump(exclude={"source"})
        return interaction_service.create_interaction(db, data, rep_id=rep_id, source=payload.source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{interaction_id}", response_model=InteractionOut)
def get_interaction(interaction_id: str, db: Session = Depends(get_db)):
    interaction = interaction_service.get_interaction(db, interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return interaction


@router.patch("/{interaction_id}", response_model=InteractionOut)
def update_interaction(interaction_id: str, payload: InteractionUpdate, db: Session = Depends(get_db)):
    changes = payload.model_dump(exclude_unset=True, exclude={"changed_by"})
    interaction = interaction_service.update_interaction(db, interaction_id, changes, payload.changed_by)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return interaction


@router.get("/", response_model=list[InteractionOut])
def list_interactions(hcp_id: str, db: Session = Depends(get_db)):
    return interaction_service.list_interactions_for_hcp(db, hcp_id)
