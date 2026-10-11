from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_api_key
from app.engine_client import engine_router
from app.persistence.db import get_db
from app.persistence.models import EngineProfile
from app.schemas.dto import EngineProfileIn, EngineProfileOut

router = APIRouter(prefix="/api/engine-profiles", tags=["engines"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[EngineProfileOut])
def list_profiles(db: Session = Depends(get_db)):
    return db.query(EngineProfile).order_by(EngineProfile.created_at.desc()).all()


@router.post("", response_model=EngineProfileOut)
def create_profile(body: EngineProfileIn, db: Session = Depends(get_db)):
    row = EngineProfile(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/{profile_id}", response_model=EngineProfileOut)
def update_profile(profile_id: str, body: EngineProfileIn, db: Session = Depends(get_db)):
    row = db.get(EngineProfile, profile_id)
    if not row:
        raise HTTPException(404, "profile not found")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{profile_id}/health")
async def profile_health(profile_id: str, db: Session = Depends(get_db)):
    row = db.get(EngineProfile, profile_id)
    if not row:
        raise HTTPException(404, "profile not found")
    return await engine_router.health(row)
