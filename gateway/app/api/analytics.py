from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.analytics import pipeline_dashboard, project_dashboard
from app.api.deps import require_api_key
from app.persistence.db import get_db
from app.persistence.models import TrackingEvent

router = APIRouter(prefix="/api/analytics", tags=["analytics"], dependencies=[Depends(require_api_key)])


@router.get("/dashboard")
def dashboard(project_id: str | None = None, pipeline_id: str | None = None, db: Session = Depends(get_db)):
    if pipeline_id:
        card = pipeline_dashboard(db, pipeline_id)
        if not card:
            raise HTTPException(404, "pipeline not found")
        return card
    return project_dashboard(db, project_id)


@router.get("/events")
def list_events(
    project_id: str | None = None,
    pipeline_id: str | None = None,
    event: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(TrackingEvent)
    if project_id:
        q = q.filter(TrackingEvent.project_id == project_id)
    if pipeline_id:
        q = q.filter(TrackingEvent.pipeline_id == pipeline_id)
    if event:
        q = q.filter(TrackingEvent.event == event)
    rows = q.order_by(TrackingEvent.created_at.desc()).limit(min(limit, 500)).all()
    return [
        {
            "id": r.id,
            "event": r.event,
            "project_id": r.project_id,
            "pipeline_id": r.pipeline_id,
            "session_id": r.session_id,
            "run_id": r.run_id,
            "case_id": r.case_id,
            "confidence": r.confidence,
            "props": r.props_json or {},
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
