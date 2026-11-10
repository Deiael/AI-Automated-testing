from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_auth
from app.persistence.db import get_db
from app.persistence.models import Project, VersionBaseline
from app.services.runner import run_regression
from app.services.version_regression import (
    build_plan,
    generate_from_plan,
    save_baseline,
    _baseline_out,
)

router = APIRouter(prefix="/api/regression", tags=["regression"], dependencies=[Depends(require_auth)])


class BaselineIn(BaseModel):
    project_id: str
    pipeline_id: str | None = None
    name: str = "v1"
    note: str = ""


class PlanIn(BaseModel):
    project_id: str
    pipeline_id: str | None = None
    baseline_id: str


class GenerateIn(PlanIn):
    confirm: bool = True
    execute: bool = False


@router.get("/baselines")
def list_baselines(project_id: str, pipeline_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(VersionBaseline).filter(VersionBaseline.project_id == project_id)
    if pipeline_id:
        q = q.filter((VersionBaseline.pipeline_id == pipeline_id) | (VersionBaseline.pipeline_id.is_(None)))
    rows = q.order_by(VersionBaseline.created_at.desc()).all()
    return [_baseline_out(r) for r in rows]


@router.post("/baselines")
def create_baseline(body: BaselineIn, db: Session = Depends(get_db)):
    if not db.get(Project, body.project_id):
        raise HTTPException(404, "project not found")
    row = save_baseline(
        db,
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        name=body.name,
        note=body.note,
    )
    return _baseline_out(row)


@router.delete("/baselines/{baseline_id}")
def delete_baseline(baseline_id: str, db: Session = Depends(get_db)):
    row = db.get(VersionBaseline, baseline_id)
    if not row:
        raise HTTPException(404, "baseline not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/plan")
def plan_regression(body: PlanIn, db: Session = Depends(get_db)):
    if not db.get(Project, body.project_id):
        raise HTTPException(404, "project not found")
    try:
        return build_plan(
            db,
            project_id=body.project_id,
            pipeline_id=body.pipeline_id,
            baseline_id=body.baseline_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/generate")
async def generate_regression(body: GenerateIn, db: Session = Depends(get_db)):
    if not db.get(Project, body.project_id):
        raise HTTPException(404, "project not found")
    try:
        plan = build_plan(
            db,
            project_id=body.project_id,
            pipeline_id=body.pipeline_id,
            baseline_id=body.baseline_id,
        )
        gen = generate_from_plan(
            db,
            project_id=body.project_id,
            pipeline_id=body.pipeline_id,
            plan=plan,
            confirm=body.confirm,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    result: dict = {"plan": plan, "generated": gen}
    if body.execute and gen.get("case_ids"):
        try:
            run = await run_regression(
                db,
                project_id=body.project_id,
                pipeline_id=body.pipeline_id,
                case_ids=gen["case_ids"],
                trigger="version-regression",
            )
            result["run"] = run
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(500, str(exc)) from exc
    elif body.execute and not gen.get("case_ids"):
        result["run"] = {"skipped": True, "reason": "no cases generated"}
    return result
