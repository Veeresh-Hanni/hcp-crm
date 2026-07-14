from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.hcp import HCPCreate, HCPOut
from app.services import hcp_service

router = APIRouter(prefix="/api/hcps", tags=["hcps"])


@router.get("/", response_model=list[dict])
def search_hcps(search: str = "", db: Session = Depends(get_db)):
    if not search:
        return []
    return hcp_service.search_hcps(db, search)


@router.get("/{hcp_id}", response_model=HCPOut)
def get_hcp(hcp_id: str, db: Session = Depends(get_db)):
    from app.models import HCP

    hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
    if not hcp:
        raise HTTPException(status_code=404, detail="HCP not found")
    return hcp


@router.post("/", response_model=HCPOut)
def create_hcp(payload: HCPCreate, db: Session = Depends(get_db)):
    return hcp_service.create_hcp(db, payload.model_dump())
