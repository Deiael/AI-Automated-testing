from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_api_key
from app.persistence.db import get_db
from app.persistence.models import TestCase, TestPoint, TestReport, TestRun
from app.schemas.dto import ArtifactPatch, TestRunCreate

router = APIRouter(prefix="/api", tags=["artifacts"], dependencies=[Depends(require_api_key)])


@router.get("/test-points")
def list_test_points(project_id: str, db: Session = Depends(get_db)):
    return db.query(TestPoint).filter(TestPoint.project_id == project_id).order_by(TestPoint.created_at.desc()).all()


@router.patch("/test-points/{point_id}")
def patch_test_point(point_id: str, body: ArtifactPatch, db: Session = Depends(get_db)):
    row = db.get(TestPoint, point_id)
    if not row:
        raise HTTPException(404, "not found")
    if body.title is not None:
        row.title = body.title
    if body.content_json is not None:
        row.content_json = body.content_json
    if body.status is not None:
        row.status = body.status
    db.commit()
    db.refresh(row)
    return row


@router.get("/test-cases")
def list_test_cases(project_id: str, db: Session = Depends(get_db)):
    return db.query(TestCase).filter(TestCase.project_id == project_id).order_by(TestCase.created_at.desc()).all()


@router.patch("/test-cases/{case_id}")
def patch_test_case(case_id: str, body: ArtifactPatch, db: Session = Depends(get_db)):
    row = db.get(TestCase, case_id)
    if not row:
        raise HTTPException(404, "not found")
    if body.title is not None:
        row.title = body.title
    if body.content_json is not None:
        row.content_json = body.content_json
    if body.status is not None:
        row.status = body.status
    db.commit()
    db.refresh(row)
    return row


@router.post("/test-runs")
def create_run(body: TestRunCreate, db: Session = Depends(get_db)):
    row = TestRun(project_id=body.project_id, case_ids_json=body.case_ids, status="PENDING")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/test-runs")
def list_runs(project_id: str, db: Session = Depends(get_db)):
    return db.query(TestRun).filter(TestRun.project_id == project_id).order_by(TestRun.created_at.desc()).all()


@router.get("/test-reports/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)):
    row = db.get(TestReport, report_id)
    if not row:
        raise HTTPException(404, "not found")
    return row


@router.get("/test-reports")
def list_reports(run_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(TestReport)
    if run_id:
        q = q.filter(TestReport.run_id == run_id)
    return q.order_by(TestReport.created_at.desc()).all()
