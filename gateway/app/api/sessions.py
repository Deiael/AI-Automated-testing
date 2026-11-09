from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ai_test_contracts import ChatMessage, ContextChunk, EngineRequest, FlowType, RuntimeConfig, TemplateSpec
from app.api.deps import require_api_key
from app.engine_client import engine_router
from app.persistence.db import get_db
from app.persistence.models import (
    CaseTemplate,
    Message,
    Project,
    ProjectMcpServer,
    ProjectSkill,
    Session as ChatSession,
    TestCase,
    TestPoint,
    TestReport,
    TestRun,
)
from app.analytics import emit
from app.postprocess import score_test_case_detail, summarize_confidences
from app.rag import rag_service
from app.schemas.dto import ChatIn, MessageOut, SessionCreate, SessionOut

router = APIRouter(prefix="/api/sessions", tags=["sessions"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=SessionOut)
def create_session(body: SessionCreate, db: Session = Depends(get_db)):
    if body.flow_type not in {f.value for f in FlowType}:
        raise HTTPException(400, detail={"code": "GATEWAY_VALIDATION", "message": "invalid flow_type"})
    if not db.get(Project, body.project_id):
        raise HTTPException(404, "project not found")
    row = ChatSession(
        project_id=body.project_id,
        pipeline_id=body.pipeline_id,
        flow_type=body.flow_type,
        title=body.title or body.flow_type,
        template_id=body.template_id,
        engine_profile_id=body.engine_profile_id,
        status="CREATED",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: str, db: Session = Depends(get_db)):
    row = db.get(ChatSession, session_id)
    if not row:
        raise HTTPException(404, "session not found")
    return row


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def list_messages(session_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .all()
    )


@router.post("/{session_id}/chat")
async def chat(session_id: str, body: ChatIn, db: Session = Depends(get_db)):
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(404, "session not found")
    project = db.get(Project, session.project_id)
    if not project:
        raise HTTPException(404, "project not found")

    user_msg = Message(session_id=session_id, role="user", content=body.message, event_type="message")
    db.add(user_msg)
    session.status = "STREAMING"
    db.commit()

    profile = engine_router.resolve(db, project.id, body.engine_profile_id or session.engine_profile_id)
    # Prefer this pipeline's requirement docs so multiple pipelines don't cross-contaminate.
    search_query = body.message
    if session.pipeline_id and len((body.message or "").strip()) < 24:
        search_query = f"{body.message} {session.title or '需求'}".strip()
    chunks = await rag_service.search(
        project.id,
        search_query,
        db=db,
        pipeline_id=session.pipeline_id,
    )
    history = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    template = None
    if session.template_id:
        tpl = db.get(CaseTemplate, session.template_id)
        if tpl:
            template = TemplateSpec(name=tpl.name, schema_json=tpl.schema_json or {}, prompt_hint=tpl.prompt_hint or "")
    elif session.flow_type == FlowType.TEST_CASE.value:
        tpl = db.query(CaseTemplate).filter(CaseTemplate.project_id == project.id).first()
        if tpl:
            template = TemplateSpec(name=tpl.name, schema_json=tpl.schema_json or {}, prompt_hint=tpl.prompt_hint or "")

    artifacts: dict[str, Any] = {"test_points": [], "test_cases": []}
    if body.test_point_ids:
        for tp in db.query(TestPoint).filter(TestPoint.id.in_(body.test_point_ids)).all():
            artifacts["test_points"].append({"id": tp.id, **(tp.content_json or {}), "title": tp.title})
    else:
        tp_q = db.query(TestPoint).filter(TestPoint.project_id == project.id, TestPoint.status == "CONFIRMED")
        if session.pipeline_id:
            tp_q = tp_q.filter(TestPoint.pipeline_id == session.pipeline_id)
        confirmed = tp_q.limit(20).all()
        artifacts["test_points"] = [{"id": tp.id, **(tp.content_json or {}), "title": tp.title} for tp in confirmed]

    if body.test_case_ids:
        for tc in db.query(TestCase).filter(TestCase.id.in_(body.test_case_ids)).all():
            artifacts["test_cases"].append(_case_artifact(tc))
    elif session.flow_type == FlowType.TEST_EXECUTE.value:
        tc_q = db.query(TestCase).filter(TestCase.project_id == project.id, TestCase.status == "CONFIRMED")
        if session.pipeline_id:
            tc_q = tc_q.filter(TestCase.pipeline_id == session.pipeline_id)
        cases = tc_q.limit(50).all()
        artifacts["test_cases"] = [_case_artifact(tc) for tc in cases]

    skills = (
        db.query(ProjectSkill)
        .filter(ProjectSkill.project_id == project.id, ProjectSkill.enabled.is_(True))
        .order_by(ProjectSkill.created_at.asc())
        .all()
    )
    artifacts["skills"] = [
        {"id": s.id, "name": s.name, "description": s.description or "", "content": s.content or ""}
        for s in skills
    ]

    mcp_rows = (
        db.query(ProjectMcpServer)
        .filter(ProjectMcpServer.project_id == project.id, ProjectMcpServer.enabled.is_(True))
        .all()
    )
    mcp_servers: list[dict[str, Any]] = []
    mcp_tools: list[dict[str, Any]] = []
    for srv in mcp_rows:
        mcp_servers.append(
            {
                "id": srv.id,
                "name": srv.name,
                "transport": srv.transport,
                "url": srv.url or "",
                "headers": srv.headers_json or {},
            }
        )
        for tool in srv.tools_cache_json or []:
            if isinstance(tool, dict):
                mcp_tools.append(
                    {
                        "server_id": srv.id,
                        "server_name": srv.name,
                        "transport": srv.transport,
                        "url": srv.url or "",
                        "headers": srv.headers_json or {},
                        "name": tool.get("name"),
                        "description": tool.get("description") or "",
                        "inputSchema": tool.get("inputSchema") or tool.get("input_schema") or {},
                    }
                )
    artifacts["mcp_servers"] = mcp_servers
    artifacts["mcp_tools"] = mcp_tools

    context_chunks = [ContextChunk(doc_id=c.doc_id, title=c.title, text=c.text, score=c.score) for c in chunks]
    for s in skills:
        text = (s.content or "").strip()
        if not text:
            continue
        context_chunks.append(
            ContextChunk(
                doc_id=f"skill:{s.id}",
                title=f"Skill · {s.name}",
                text=text,
                score=1.0,
            )
        )
    if mcp_tools:
        lines = []
        for t in mcp_tools[:40]:
            lines.append(f"- [{t.get('server_name')}] {t.get('name')}: {t.get('description')}")
        context_chunks.append(
            ContextChunk(
                doc_id="mcp:tools",
                title="MCP tools",
                text="可用 MCP 工具：\n" + "\n".join(lines),
                score=1.0,
            )
        )

    req = EngineRequest(
        request_id=str(uuid.uuid4()),
        flow=FlowType(session.flow_type),
        model=profile.model,
        session_id=session_id,
        messages=[ChatMessage(role=m.role if m.role in ("user", "assistant", "system") else "user", content=m.content) for m in history],
        context_chunks=context_chunks,
        template=template,
        artifacts=artifacts,
        runtime=RuntimeConfig(
            base_url=project.runtime_base_url or "",
            headers=project.runtime_headers or {},
            variables=project.runtime_variables or {},
        ),
    )

    run_row: TestRun | None = None
    if session.flow_type == FlowType.TEST_EXECUTE.value:
        run_row = TestRun(
            project_id=project.id,
            pipeline_id=session.pipeline_id,
            session_id=session_id,
            case_ids_json=[c.get("id") for c in artifacts["test_cases"] if c.get("id")],
            status="RUNNING",
        )
        db.add(run_row)
        db.commit()
        db.refresh(run_row)

    async def event_gen():
        assistant_parts: list[str] = []
        need_user = False
        try:
            async for ev in engine_router.stream(profile, req):
                data = dict(ev.data or {})
                if ev.event == "token":
                    assistant_parts.append(str(data.get("delta") or ""))
                elif ev.event == "message":
                    content = str(data.get("content") or "")
                    if content and not assistant_parts:
                        assistant_parts.append(content)
                    db.add(Message(session_id=session_id, role="assistant", content=content, event_type="message"))
                    db.commit()
                elif ev.event == "ask_user":
                    need_user = True
                    db.add(
                        Message(
                            session_id=session_id,
                            role="assistant",
                            content=json.dumps(data, ensure_ascii=False),
                            event_type="ask_user",
                        )
                    )
                    db.commit()
                elif ev.event == "artifact":
                    kind = data.get("kind")
                    payload = data.get("payload") or {}
                    artifact_id = _persist_artifact(
                        db,
                        session=session,
                        project_id=project.id,
                        kind=kind,
                        payload=payload,
                        template=template,
                        rag_texts=[c.text for c in chunks],
                        run_row=run_row,
                    )
                    extra: dict[str, Any] = {"artifact_id": artifact_id, "gateway_ts": True, "payload": payload}
                    if payload.get("confidence") is not None:
                        extra["confidence"] = payload.get("confidence")
                    data = {**data, **extra}
                elif ev.event == "done":
                    session.status = "WAITING_USER" if need_user else "COMPLETED"
                    if run_row and run_row.status == "RUNNING":
                        run_row.status = "DONE"
                    db.commit()
                    if session.flow_type == FlowType.TEST_CASE.value:
                        _emit_generation_summary(db, session=session, project_id=project.id)

                yield f"data: {json.dumps({'event': ev.event, 'data': data}, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            session.status = "FAILED"
            db.commit()
            err = {"event": "error", "data": {"code": "ENGINE_STREAM_ERROR", "message": str(exc)}}
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _persist_artifact(
    db: Session,
    *,
    session: ChatSession,
    project_id: str,
    kind: str,
    payload: dict[str, Any],
    template: TemplateSpec | None,
    rag_texts: list[str],
    run_row: TestRun | None,
) -> str | None:
    if kind == "test_point":
        row = TestPoint(
            project_id=project_id,
            pipeline_id=session.pipeline_id,
            session_id=session.id,
            title=str(payload.get("title") or "未命名测试点"),
            content_json=payload,
            status="DRAFT",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    if kind == "test_case":
        detail = score_test_case_detail(payload, (template.fields_schema if template else None), rag_texts)
        conf = float(detail["score"])
        stored = {**payload, "_confidence": detail}
        row = TestCase(
            project_id=project_id,
            pipeline_id=session.pipeline_id,
            session_id=session.id,
            template_id=session.template_id,
            title=str(payload.get("title") or "未命名用例"),
            content_json=stored,
            confidence=conf,
            status="DRAFT",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        emit(
            db,
            event="case_generated",
            project_id=project_id,
            pipeline_id=session.pipeline_id,
            session_id=session.id,
            case_id=row.id,
            confidence=conf,
            props={"title": row.title, **detail},
        )
        payload["_confidence"] = detail
        payload["confidence"] = conf
        payload["title"] = row.title
        return row.id
    if kind == "report" and run_row:
        return _persist_report(db, session=session, project_id=project_id, payload=payload, run_row=run_row)
    return None


def _persist_report(
    db: Session,
    *,
    session: ChatSession,
    project_id: str,
    payload: dict[str, Any],
    run_row: TestRun,
) -> str:
    details = payload.get("details") or []
    if not isinstance(details, list):
        details = []
    case_map = _case_lookup(db, run_row)
    enriched: list[dict[str, Any]] = []
    for item in details:
        if not isinstance(item, dict):
            continue
        case_row = _match_case(item, case_map)
        conf = float(case_row.confidence or 0) if case_row else float(item.get("confidence") or 0)
        merged = {
            **item,
            "case_id": (case_row.id if case_row else item.get("case_id")),
            "confidence": conf,
            "confidence_band": (case_row.content_json or {}).get("_confidence", {}).get("band") if case_row else None,
        }
        enriched.append(merged)
        emit(
            db,
            event="case_executed",
            project_id=project_id,
            pipeline_id=session.pipeline_id or run_row.pipeline_id,
            session_id=session.id,
            run_id=run_row.id,
            case_id=merged.get("case_id"),
            confidence=conf,
            props={
                "ok": bool(merged.get("ok")),
                "status_code": merged.get("status_code"),
                "case_title": merged.get("case_title"),
                "scope": "single" if len(run_row.case_ids_json or []) == 1 else "suite",
            },
            commit=False,
        )

    summary = dict(payload.get("summary") or {})
    conf_summary = summarize_confidences([float(d.get("confidence") or 0) for d in enriched])
    passed = int(summary.get("passed") or sum(1 for d in enriched if d.get("ok")))
    failed = int(summary.get("failed") or sum(1 for d in enriched if not d.get("ok")))
    total = int(summary.get("total") or len(enriched))
    time_ms = int(summary.get("time_ms") or sum(int(d.get("time_ms") or 0) for d in enriched))
    failed_titles = summary.get("failed_titles") or [d.get("case_title") for d in enriched if not d.get("ok")]
    summary.update(
        {
            "total": total,
            "passed": passed,
            "failed": failed,
            "time_ms": time_ms,
            "failed_titles": [t for t in failed_titles if t],
            "confidence_avg": conf_summary["avg"],
            "confidence": conf_summary,
            "scope": "single" if len(run_row.case_ids_json or []) == 1 else "suite",
        }
    )
    report = TestReport(
        run_id=run_row.id,
        summary_json=summary,
        detail_json={
            "details": enriched,
            "variables": payload.get("variables") or {},
            "mcp_log": payload.get("mcp_log") or [],
        },
        status="DONE",
    )
    run_row.status = "DONE"
    db.add(report)
    db.commit()
    db.refresh(report)
    emit(
        db,
        event="run_confidence",
        project_id=project_id,
        pipeline_id=session.pipeline_id or run_row.pipeline_id,
        session_id=session.id,
        run_id=run_row.id,
        confidence=conf_summary["avg"],
        props={
            "scope": summary["scope"],
            "total": total,
            "passed": passed,
            "failed": failed,
            **conf_summary,
        },
    )
    failed_details = [d for d in enriched if not d.get("ok")]
    if failed_details:
        try:
            from app.services.defects import sync_failures_to_issues

            defects = sync_failures_to_issues(
                db,
                project_id=project_id,
                pipeline_id=session.pipeline_id or run_row.pipeline_id,
                run_row=run_row,
                failed_details=failed_details,
            )
            payload["defects"] = defects
        except Exception:  # noqa: BLE001
            payload["defects"] = []
    payload["summary"] = summary
    payload["details"] = enriched
    return report.id


def _case_artifact(tc: TestCase) -> dict[str, Any]:
    from app.export_cases import engine_artifact

    return engine_artifact(tc)


def _emit_generation_summary(db: Session, *, session: ChatSession, project_id: str) -> None:
    rows = db.query(TestCase).filter(TestCase.session_id == session.id).all()
    if not rows:
        return
    summary = summarize_confidences([float(c.confidence or 0) for c in rows])
    emit(
        db,
        event="generation_confidence",
        project_id=project_id,
        pipeline_id=session.pipeline_id,
        session_id=session.id,
        confidence=summary["avg"],
        props={"scope": "suite", **summary},
    )


def _case_lookup(db: Session, run_row: TestRun) -> dict[str, TestCase]:
    ids = [cid for cid in (run_row.case_ids_json or []) if cid]
    rows: list[TestCase] = []
    if ids:
        rows = db.query(TestCase).filter(TestCase.id.in_(ids)).all()
    by_id = {r.id: r for r in rows}
    by_title = {r.title: r for r in rows}
    return {"id": by_id, "title": by_title}  # type: ignore[return-value]


def _match_case(item: dict[str, Any], lookup: dict[str, Any]) -> TestCase | None:
    by_id: dict[str, TestCase] = lookup.get("id") or {}
    by_title: dict[str, TestCase] = lookup.get("title") or {}
    cid = item.get("case_id")
    if cid and cid in by_id:
        return by_id[cid]
    title = item.get("case_title")
    if title and title in by_title:
        return by_title[title]
    return None
