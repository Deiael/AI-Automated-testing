from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from ai_test_contracts import (
    ChatMessage,
    EngineRequest,
    FlowType,
    RuntimeConfig,
)
from app.engine_client.router import engine_router
from app.export_cases import engine_artifact
from app.persistence.models import Project, TestCase, TestReport, TestRun
from app.postprocess.confidence import summarize_confidences
from app.services.defects import sync_failures_to_issues

logger = logging.getLogger(__name__)


async def run_regression(
    db: Session,
    *,
    project_id: str,
    pipeline_id: str | None = None,
    case_ids: list[str] | None = None,
    engine_profile_id: str | None = None,
    trigger: str = "manual",
    env_id: str | None = None,
) -> dict[str, Any]:
    project = db.get(Project, project_id)
    if not project:
        raise ValueError("project not found")

    q = db.query(TestCase).filter(TestCase.project_id == project_id, TestCase.status == "CONFIRMED")
    if pipeline_id:
        q = q.filter(TestCase.pipeline_id == pipeline_id)
    if case_ids:
        q = q.filter(TestCase.id.in_(case_ids))
    cases = q.order_by(TestCase.created_at.asc()).all()
    if not cases:
        raise ValueError("no confirmed test cases to run")

    profile = engine_router.resolve(db, project_id, engine_profile_id)
    run_row = TestRun(
        project_id=project_id,
        pipeline_id=pipeline_id,
        session_id=None,
        case_ids_json=[c.id for c in cases],
        status="RUNNING",
    )
    db.add(run_row)
    db.commit()
    db.refresh(run_row)

    from app.services.runtime_env import resolve_env

    env = resolve_env(project, env_id)
    artifacts = {"test_cases": [engine_artifact(c) for c in cases], "test_points": []}
    req = EngineRequest(
        request_id=str(uuid.uuid4()),
        flow=FlowType.TEST_EXECUTE,
        model=profile.model,
        session_id=f"ci-{run_row.id}",
        messages=[
            ChatMessage(
                role="user",
                content=f"Run regression suite ({trigger}). Execute all provided test cases and return the report.",
            )
        ],
        context_chunks=[],
        template=None,
        artifacts=artifacts,
        runtime=RuntimeConfig(
            base_url=env.get("base_url") or "",
            headers=env.get("headers") or {},
            variables=env.get("variables") or {},
            env_id=str(env.get("id") or ""),
            env_name=str(env.get("name") or ""),
            timeout_sec=float(env.get("timeout_sec") or 30),
        ),
    )

    report_payload: dict[str, Any] | None = None
    error_msg: str | None = None
    async for ev in engine_router.stream(profile, req):
        if ev.event == "artifact" and (ev.data or {}).get("kind") == "report":
            report_payload = (ev.data or {}).get("payload") or {}
        elif ev.event == "error":
            error_msg = str((ev.data or {}).get("message") or "engine error")

    if not report_payload:
        run_row.status = "FAILED"
        db.commit()
        raise RuntimeError(error_msg or "engine did not return a report")

    details = report_payload.get("details") or []
    if not isinstance(details, list):
        details = []
    by_id = {c.id: c for c in cases}
    by_title = {c.title: c for c in cases}
    enriched: list[dict[str, Any]] = []
    for item in details:
        if not isinstance(item, dict):
            continue
        case_row = None
        if item.get("case_id") and str(item["case_id"]) in by_id:
            case_row = by_id[str(item["case_id"])]
        elif item.get("case_title") and item["case_title"] in by_title:
            case_row = by_title[str(item["case_title"])]
        conf = float(case_row.confidence or 0) if case_row else float(item.get("confidence") or 0)
        enriched.append(
            {
                **item,
                "case_id": case_row.id if case_row else item.get("case_id"),
                "confidence": conf,
            }
        )

    summary = dict(report_payload.get("summary") or {})
    conf_summary = summarize_confidences([float(d.get("confidence") or 0) for d in enriched])
    passed = int(summary.get("passed") or sum(1 for d in enriched if d.get("ok")))
    failed = int(summary.get("failed") or sum(1 for d in enriched if not d.get("ok")))
    total = int(summary.get("total") or len(enriched))
    summary.update(
        {
            "total": total,
            "passed": passed,
            "failed": failed,
            "confidence_avg": conf_summary["avg"],
            "confidence": conf_summary,
            "trigger": trigger,
            "scope": "suite",
        }
    )
    report = TestReport(
        run_id=run_row.id,
        summary_json=summary,
        detail_json={"details": enriched, "variables": report_payload.get("variables") or {}},
        status="DONE",
    )
    run_row.status = "DONE" if failed == 0 else "FAILED"
    db.add(report)
    db.commit()
    db.refresh(report)

    defect_results: list[dict[str, Any]] = []
    failed_details = [d for d in enriched if not d.get("ok")]
    if failed_details:
        try:
            defect_results = sync_failures_to_issues(
                db,
                project_id=project_id,
                pipeline_id=pipeline_id,
                run_row=run_row,
                failed_details=failed_details,
            )
        except Exception:  # noqa: BLE001
            logger.exception("defect sync failed")

    return {
        "run_id": run_row.id,
        "report_id": report.id,
        "status": run_row.status,
        "summary": summary,
        "defects": defect_results,
        "case_count": len(cases),
    }
