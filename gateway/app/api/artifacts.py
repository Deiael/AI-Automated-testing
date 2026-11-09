from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import require_api_key
from app.export_cases import case_payload, export_json, export_postman
from app.persistence.db import get_db
from app.persistence.models import CaseTemplate, Project, TestCase, TestPoint, TestReport, TestRun
from app.postprocess import score_test_case_detail
from app.schemas.dto import ArtifactPatch, TestCaseCreate, TestRunCreate

router = APIRouter(prefix="/api", tags=["artifacts"], dependencies=[Depends(require_api_key)])


@router.get("/test-points")
def list_test_points(project_id: str, pipeline_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(TestPoint).filter(TestPoint.project_id == project_id)
    if pipeline_id:
        q = q.filter(TestPoint.pipeline_id == pipeline_id)
    return q.order_by(TestPoint.created_at.desc()).all()


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
def list_test_cases(project_id: str, pipeline_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(TestCase).filter(TestCase.project_id == project_id)
    if pipeline_id:
        q = q.filter(TestCase.pipeline_id == pipeline_id)
    return q.order_by(TestCase.created_at.desc()).all()


@router.get("/test-cases/export")
def export_test_cases(
    project_id: str,
    pipeline_id: str | None = None,
    fmt: str = Query("json", alias="format"),
    db: Session = Depends(get_db),
):
    q = db.query(TestCase).filter(TestCase.project_id == project_id)
    if pipeline_id:
        q = q.filter(TestCase.pipeline_id == pipeline_id)
    rows = q.order_by(TestCase.created_at.asc()).all()
    project = db.get(Project, project_id)
    if fmt == "postman":
        payload = export_postman(rows, project)
        filename = "ai-test.postman_collection.json"
    else:
        payload = export_json(rows)
        filename = "ai-test-cases.json"
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/test-cases")
def create_test_case(body: TestCaseCreate, db: Session = Depends(get_db)):
    content = dict(body.content_json or {})
    title = body.title or str(content.get("title") or "未命名用例")
    schema = _template_schema(db, body.template_id)
    detail = score_test_case_detail(content, schema, [])
    content["_confidence"] = detail
    row = TestCase(
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        template_id=body.template_id,
        title=title,
        content_json=content,
        confidence=float(detail["score"]),
        status=body.status or "DRAFT",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/test-cases/{case_id}")
def patch_test_case(case_id: str, body: ArtifactPatch, db: Session = Depends(get_db)):
    row = db.get(TestCase, case_id)
    if not row:
        raise HTTPException(404, "not found")
    if body.title is not None:
        row.title = body.title
    if body.content_json is not None:
        content = dict(body.content_json)
        schema = _template_schema(db, row.template_id)
        detail = score_test_case_detail(content, schema, [])
        content["_confidence"] = detail
        row.content_json = content
        row.confidence = float(detail["score"])
        if body.title is None and content.get("title"):
            row.title = str(content["title"])
    if body.status is not None:
        row.status = body.status
    db.commit()
    db.refresh(row)
    return row


@router.delete("/test-cases/{case_id}")
def delete_test_case(case_id: str, db: Session = Depends(get_db)):
    row = db.get(TestCase, case_id)
    if not row:
        raise HTTPException(404, "not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/test-runs")
def create_run(body: TestRunCreate, db: Session = Depends(get_db)):
    row = TestRun(project_id=body.project_id, case_ids_json=body.case_ids, status="PENDING")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/test-runs")
def list_runs(project_id: str, pipeline_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(TestRun).filter(TestRun.project_id == project_id)
    if pipeline_id:
        q = q.filter(TestRun.pipeline_id == pipeline_id)
    return q.order_by(TestRun.created_at.desc()).all()


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


def _template_schema(db: Session, template_id: str | None) -> dict | None:
    if not template_id:
        return None
    tpl = db.get(CaseTemplate, template_id)
    return tpl.schema_json if tpl else None
