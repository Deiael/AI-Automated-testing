from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_auth
from app.persistence.db import get_db
from app.persistence.models import DefectIssue, Project, ScheduleJob
from app.services.defects import list_defects
from app.services.runner import run_regression
from app.services.scheduler import resolve_cron

router = APIRouter(tags=["ci"], dependencies=[Depends(require_auth)])


class CiRunIn(BaseModel):
    project_id: str
    pipeline_id: Optional[str] = None
    case_ids: list[str] = Field(default_factory=list)
    engine_profile_id: Optional[str] = None
    trigger: str = "ci"


class ScheduleIn(BaseModel):
    project_id: str
    pipeline_id: str
    name: str = "regression"
    cron: str = "daily"
    enabled: bool = True


class SchedulePatch(BaseModel):
    name: Optional[str] = None
    cron: Optional[str] = None
    enabled: Optional[bool] = None


class DefectConfigIn(BaseModel):
    enabled: bool = False
    provider: str = "github"  # github | webhook
    token: str = ""
    repo: str = ""
    webhook_url: str = ""
    labels: list[str] = Field(default_factory=lambda: ["ai-test", "auto"])


@router.post("/api/ci/run")
async def ci_run(body: CiRunIn, db: Session = Depends(get_db)):
    if not db.get(Project, body.project_id):
        raise HTTPException(404, "project not found")
    try:
        result = await run_regression(
            db,
            project_id=body.project_id,
            pipeline_id=body.pipeline_id,
            case_ids=body.case_ids or None,
            engine_profile_id=body.engine_profile_id,
            trigger=body.trigger or "ci",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, str(exc)) from exc
    return result


@router.get("/api/schedules")
def list_schedules(project_id: str | None = None, pipeline_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(ScheduleJob)
    if project_id:
        q = q.filter(ScheduleJob.project_id == project_id)
    if pipeline_id:
        q = q.filter(ScheduleJob.pipeline_id == pipeline_id)
    rows = q.order_by(ScheduleJob.created_at.desc()).all()
    return [_schedule_out(r) for r in rows]


@router.post("/api/schedules")
def create_schedule(body: ScheduleIn, db: Session = Depends(get_db)):
    if not db.get(Project, body.project_id):
        raise HTTPException(404, "project not found")
    # validate cron
    try:
        resolve_cron(body.cron)
        from apscheduler.triggers.cron import CronTrigger

        CronTrigger.from_crontab(resolve_cron(body.cron), timezone="UTC")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"invalid cron: {exc}") from exc
    row = ScheduleJob(
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        name=body.name,
        cron=body.cron,
        enabled=body.enabled,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _schedule_out(row)


@router.patch("/api/schedules/{job_id}")
def patch_schedule(job_id: str, body: SchedulePatch, db: Session = Depends(get_db)):
    row = db.get(ScheduleJob, job_id)
    if not row:
        raise HTTPException(404, "schedule not found")
    data = body.model_dump(exclude_unset=True)
    if "cron" in data and data["cron"] is not None:
        try:
            from apscheduler.triggers.cron import CronTrigger

            CronTrigger.from_crontab(resolve_cron(data["cron"]), timezone="UTC")
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, f"invalid cron: {exc}") from exc
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _schedule_out(row)


@router.delete("/api/schedules/{job_id}")
def delete_schedule(job_id: str, db: Session = Depends(get_db)):
    row = db.get(ScheduleJob, job_id)
    if not row:
        raise HTTPException(404, "schedule not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/api/schedules/{job_id}/run")
async def run_schedule_now(job_id: str, db: Session = Depends(get_db)):
    row = db.get(ScheduleJob, job_id)
    if not row:
        raise HTTPException(404, "schedule not found")
    try:
        result = await run_regression(
            db,
            project_id=row.project_id,
            pipeline_id=row.pipeline_id,
            trigger=f"schedule-manual:{row.id}",
        )
    except Exception as exc:  # noqa: BLE001
        row.last_run_at = datetime.utcnow()
        row.last_status = "FAILED"
        row.last_summary_json = {"error": str(exc)}
        db.commit()
        raise HTTPException(500, str(exc)) from exc
    row.last_run_at = datetime.utcnow()
    row.last_status = result.get("status") or "DONE"
    row.last_summary_json = result.get("summary") or {}
    db.commit()
    return result


@router.get("/api/projects/{project_id}/defect-config")
def get_defect_config(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "project not found")
    cfg = dict(project.defect_config or {})
    # mask token
    if cfg.get("token"):
        cfg = {**cfg, "token": "***" if len(str(cfg["token"])) < 8 else str(cfg["token"])[:4] + "****"}
    return cfg


@router.put("/api/projects/{project_id}/defect-config")
def put_defect_config(project_id: str, body: DefectConfigIn, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "project not found")
    prev = dict(project.defect_config or {})
    data = body.model_dump()
    if data.get("token") in ("", "***") or (isinstance(data.get("token"), str) and data["token"].endswith("****")):
        data["token"] = prev.get("token") or ""
    project.defect_config = data
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(project, "defect_config")
    db.commit()
    return {"ok": True, "enabled": data.get("enabled"), "provider": data.get("provider")}


@router.get("/api/defects")
def get_defects(project_id: str, pipeline_id: str | None = None, db: Session = Depends(get_db)):
    rows = list_defects(db, project_id=project_id, pipeline_id=pipeline_id)
    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "pipeline_id": r.pipeline_id,
            "run_id": r.run_id,
            "case_id": r.case_id,
            "case_title": r.case_title,
            "provider": r.provider,
            "external_id": r.external_id,
            "external_url": r.external_url,
            "title": r.title,
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.patch("/api/defects/{issue_id}")
def patch_defect(issue_id: str, status: str = "open", db: Session = Depends(get_db)):
    row = db.get(DefectIssue, issue_id)
    if not row:
        raise HTTPException(404, "defect not found")
    row.status = status
    db.commit()
    return {"ok": True, "id": row.id, "status": row.status}


def _schedule_out(row: ScheduleJob) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "pipeline_id": row.pipeline_id,
        "name": row.name,
        "cron": row.cron,
        "cron_resolved": resolve_cron(row.cron),
        "enabled": row.enabled,
        "last_run_at": row.last_run_at,
        "last_status": row.last_status,
        "last_summary": row.last_summary_json or {},
        "created_at": row.created_at,
    }
