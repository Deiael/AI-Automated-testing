from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_api_key
from app.persistence.db import get_db
from app.persistence.models import Pipeline, Project

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"], dependencies=[Depends(require_api_key)])


class PipelineIn(BaseModel):
    name: str
    project_id: str
    description: str = ""
    step: str = "req"
    status: str = "active"


class PipelinePatch(BaseModel):
    name: str | None = None
    description: str | None = None
    project_id: str | None = None
    step: str | None = None
    status: str | None = None


class PipelineOut(BaseModel):
    id: str
    name: str
    description: str
    project_id: str
    project_name: str = ""
    step: str
    status: str
    created_at: datetime | None = None

    class Config:
        from_attributes = True


def _to_out(row: Pipeline, project_name: str = "") -> PipelineOut:
    return PipelineOut(
        id=row.id,
        name=row.name,
        description=row.description or "",
        project_id=row.project_id,
        project_name=project_name,
        step=row.step or "req",
        status=row.status or "active",
        created_at=row.created_at,
    )


@router.get("", response_model=list[PipelineOut])
def list_pipelines(db: Session = Depends(get_db)):
    rows = db.query(Pipeline).order_by(Pipeline.created_at.desc()).all()
    projects = {p.id: p.name for p in db.query(Project).all()}
    return [_to_out(r, projects.get(r.project_id, "")) for r in rows]


@router.post("", response_model=PipelineOut)
def create_pipeline(body: PipelineIn, db: Session = Depends(get_db)):
    project = db.get(Project, body.project_id)
    if not project:
        raise HTTPException(404, detail={"code": "GATEWAY_VALIDATION", "message": "关联项目不存在"})
    if body.step not in {"req", "cases", "report"}:
        raise HTTPException(400, detail={"code": "GATEWAY_VALIDATION", "message": "invalid step"})
    row = Pipeline(
        name=body.name.strip(),
        description=body.description or "",
        project_id=body.project_id,
        step=body.step,
        status=body.status or "active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row, project.name)


@router.get("/{pipeline_id}", response_model=PipelineOut)
def get_pipeline(pipeline_id: str, db: Session = Depends(get_db)):
    row = db.get(Pipeline, pipeline_id)
    if not row:
        raise HTTPException(404, "pipeline not found")
    project = db.get(Project, row.project_id)
    return _to_out(row, project.name if project else "")


@router.patch("/{pipeline_id}", response_model=PipelineOut)
def patch_pipeline(pipeline_id: str, body: PipelinePatch, db: Session = Depends(get_db)):
    row = db.get(Pipeline, pipeline_id)
    if not row:
        raise HTTPException(404, "pipeline not found")
    data = body.model_dump(exclude_unset=True)
    if "project_id" in data and data["project_id"]:
        if not db.get(Project, data["project_id"]):
            raise HTTPException(404, detail={"code": "GATEWAY_VALIDATION", "message": "关联项目不存在"})
    if "step" in data and data["step"] not in {"req", "cases", "report"}:
        raise HTTPException(400, detail={"code": "GATEWAY_VALIDATION", "message": "invalid step"})
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    project = db.get(Project, row.project_id)
    return _to_out(row, project.name if project else "")


@router.delete("/{pipeline_id}")
def delete_pipeline(pipeline_id: str, db: Session = Depends(get_db)):
    row = db.get(Pipeline, pipeline_id)
    if not row:
        raise HTTPException(404, "pipeline not found")
    db.delete(row)
    db.commit()
    return {"ok": True}
