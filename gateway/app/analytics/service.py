from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.persistence.models import Pipeline, Project, TestCase, TestReport, TestRun, TrackingEvent
from app.postprocess.confidence import summarize_confidences


def emit(
    db: Session,
    *,
    event: str,
    project_id: str | None = None,
    pipeline_id: str | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
    case_id: str | None = None,
    confidence: float | None = None,
    props: dict[str, Any] | None = None,
    commit: bool = True,
) -> TrackingEvent:
    row = TrackingEvent(
        event=event,
        project_id=project_id,
        pipeline_id=pipeline_id,
        session_id=session_id,
        run_id=run_id,
        case_id=case_id,
        confidence=confidence,
        props_json=props or {},
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    return row


def project_dashboard(db: Session, project_id: str | None = None) -> dict[str, Any]:
    q = db.query(Pipeline).order_by(Pipeline.created_at.desc())
    if project_id:
        q = q.filter(Pipeline.project_id == project_id)
    pipelines = q.all()
    projects = {p.id: p.name for p in db.query(Project).all()}
    cards = [_pipeline_card(db, row, projects.get(row.project_id, "")) for row in pipelines]
    overall_scores = [c["generation"]["avg"] for c in cards if c["generation"]["count"]]
    run_scores = [c["latest_run"]["overall_confidence"] for c in cards if c.get("latest_run")]
    return {
        "pipeline_count": len(cards),
        "overall_generation": summarize_confidences(overall_scores),
        "overall_run": summarize_confidences(run_scores),
        "pipelines": cards,
    }


def pipeline_dashboard(db: Session, pipeline_id: str) -> dict[str, Any] | None:
    row = db.get(Pipeline, pipeline_id)
    if not row:
        return None
    project = db.get(Project, row.project_id)
    return _pipeline_card(db, row, project.name if project else "", include_detail=True)


def _pipeline_card(db: Session, pipeline: Pipeline, project_name: str, include_detail: bool = False) -> dict[str, Any]:
    cases = (
        db.query(TestCase)
        .filter(TestCase.pipeline_id == pipeline.id)
        .order_by(TestCase.created_at.desc())
        .all()
    )
    gen = summarize_confidences([float(c.confidence or 0) for c in cases])
    runs = (
        db.query(TestRun)
        .filter(TestRun.pipeline_id == pipeline.id)
        .order_by(TestRun.created_at.desc())
        .all()
    )
    run_cards = [_run_card(db, run) for run in runs[:20]]
    latest = run_cards[0] if run_cards else None
    payload: dict[str, Any] = {
        "pipeline_id": pipeline.id,
        "name": pipeline.name,
        "description": pipeline.description or "",
        "project_id": pipeline.project_id,
        "project_name": project_name,
        "step": pipeline.step,
        "generation": gen,
        "run_count": len(runs),
        "latest_run": latest,
    }
    if include_detail:
        payload["cases"] = [
            {
                "id": c.id,
                "title": c.title,
                "status": c.status,
                "confidence": float(c.confidence or 0),
                "band": (c.content_json or {}).get("_confidence", {}).get("band"),
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in cases
        ]
        payload["runs"] = run_cards
        payload["events"] = _recent_events(db, pipeline.id)
    return payload


def _run_card(db: Session, run: TestRun) -> dict[str, Any]:
    report = db.query(TestReport).filter(TestReport.run_id == run.id).order_by(TestReport.created_at.desc()).first()
    summary = (report.summary_json if report else {}) or {}
    details = ((report.detail_json or {}).get("details") if report else None) or []
    case_confs: list[float] = []
    if isinstance(details, list):
        for item in details:
            if isinstance(item, dict) and item.get("confidence") is not None:
                case_confs.append(float(item["confidence"]))
    if not case_confs:
        ids = run.case_ids_json or []
        if ids:
            rows = db.query(TestCase).filter(TestCase.id.in_(ids)).all()
            case_confs = [float(c.confidence or 0) for c in rows]
    overall = float(summary.get("confidence_avg") or 0)
    if not overall and case_confs:
        overall = round(sum(case_confs) / len(case_confs), 3)
    return {
        "run_id": run.id,
        "status": run.status,
        "scope": summary.get("scope") or ("single" if len(run.case_ids_json or []) == 1 else "suite"),
        "case_count": len(run.case_ids_json or []),
        "passed": summary.get("passed"),
        "failed": summary.get("failed"),
        "total": summary.get("total"),
        "overall_confidence": overall,
        "confidence": summarize_confidences(case_confs),
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def _recent_events(db: Session, pipeline_id: str) -> list[dict[str, Any]]:
    rows = (
        db.query(TrackingEvent)
        .filter(TrackingEvent.pipeline_id == pipeline_id)
        .order_by(TrackingEvent.created_at.desc())
        .limit(80)
        .all()
    )
    return [
        {
            "id": r.id,
            "event": r.event,
            "case_id": r.case_id,
            "run_id": r.run_id,
            "confidence": r.confidence,
            "props": r.props_json or {},
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def group_events_by_day(events: list[TrackingEvent]) -> dict[str, int]:
    buckets: dict[str, int] = defaultdict(int)
    for ev in events:
        if ev.created_at:
            buckets[ev.created_at.date().isoformat()] += 1
    return dict(buckets)
