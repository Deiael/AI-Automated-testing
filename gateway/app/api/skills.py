from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_api_key
from app.persistence.db import get_db
from app.persistence.models import Project, ProjectSkill
from app.schemas.dto import SkillIn, SkillOut

router = APIRouter(prefix="/api/projects", tags=["skills"], dependencies=[Depends(require_api_key)])


@router.get("/{project_id}/skills", response_model=list[SkillOut])
def list_skills(project_id: str, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "project not found")
    return (
        db.query(ProjectSkill)
        .filter(ProjectSkill.project_id == project_id)
        .order_by(ProjectSkill.created_at.desc())
        .all()
    )


@router.post("/{project_id}/skills", response_model=SkillOut)
def create_skill(project_id: str, body: SkillIn, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "project not found")
    row = ProjectSkill(project_id=project_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/{project_id}/skills/{skill_id}", response_model=SkillOut)
def update_skill(project_id: str, skill_id: str, body: SkillIn, db: Session = Depends(get_db)):
    row = db.get(ProjectSkill, skill_id)
    if not row or row.project_id != project_id:
        raise HTTPException(404, "skill not found")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{project_id}/skills/{skill_id}")
def delete_skill(project_id: str, skill_id: str, db: Session = Depends(get_db)):
    row = db.get(ProjectSkill, skill_id)
    if not row or row.project_id != project_id:
        raise HTTPException(404, "skill not found")
    db.delete(row)
    db.commit()
    return {"ok": True}
