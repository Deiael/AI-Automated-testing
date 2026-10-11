from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_api_key
from app.persistence.db import get_db
from app.persistence.models import CaseTemplate, Project
from app.schemas.dto import ProjectIn, ProjectOut, TemplateIn, TemplateOut

router = APIRouter(prefix="/api/projects", tags=["projects"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.post("", response_model=ProjectOut)
def create_project(body: ProjectIn, db: Session = Depends(get_db)):
    row = Project(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    # default template
    tpl = CaseTemplate(
        project_id=row.id,
        name="api-case-v1",
        schema_json={
            "required": ["title", "precondition", "steps", "expected", "priority"],
            "properties": {
                "title": {"type": "string"},
                "precondition": {"type": "string"},
                "steps": {"type": "array"},
                "expected": {"type": "string"},
                "priority": {"type": "string"},
                "method": {"type": "string"},
                "path": {"type": "string"},
            },
        },
        prompt_hint="接口测试标准模板",
    )
    db.add(tpl)
    db.commit()
    return row


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    row = db.get(Project, project_id)
    if not row:
        raise HTTPException(404, "project not found")
    return row


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, body: ProjectIn, db: Session = Depends(get_db)):
    row = db.get(Project, project_id)
    if not row:
        raise HTTPException(404, "project not found")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{project_id}/templates", response_model=list[TemplateOut])
def list_templates(project_id: str, db: Session = Depends(get_db)):
    return db.query(CaseTemplate).filter(CaseTemplate.project_id == project_id).all()


@router.post("/{project_id}/templates", response_model=TemplateOut)
def create_template(project_id: str, body: TemplateIn, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "project not found")
    row = CaseTemplate(project_id=project_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/{project_id}/templates/{template_id}", response_model=TemplateOut)
def update_template(project_id: str, template_id: str, body: TemplateIn, db: Session = Depends(get_db)):
    row = db.get(CaseTemplate, template_id)
    if not row or row.project_id != project_id:
        raise HTTPException(404, "template not found")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row
