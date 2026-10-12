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
from app.postprocess import score_test_case
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
    chunks = await rag_service.search(project.id, body.message)
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
        confirmed = (
            db.query(TestPoint)
            .filter(TestPoint.project_id == project.id, TestPoint.status == "CONFIRMED")
            .limit(20)
            .all()
        )
        artifacts["test_points"] = [{"id": tp.id, **(tp.content_json or {}), "title": tp.title} for tp in confirmed]

    if body.test_case_ids:
        for tc in db.query(TestCase).filter(TestCase.id.in_(body.test_case_ids)).all():
            artifacts["test_cases"].append({"id": tc.id, **(tc.content_json or {}), "title": tc.title})
    elif session.flow_type == FlowType.TEST_EXECUTE.value:
        cases = (
            db.query(TestCase)
            .filter(TestCase.project_id == project.id, TestCase.status == "CONFIRMED")
            .limit(50)
            .all()
        )
        artifacts["test_cases"] = [{"id": tc.id, **(tc.content_json or {}), "title": tc.title} for tc in cases]

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
    mcp_tools: list[dict[str, Any]] = []
    for srv in mcp_rows:
        for tool in srv.tools_cache_json or []:
            if isinstance(tool, dict):
                mcp_tools.append(
                    {
                        "server_id": srv.id,
                        "server_name": srv.name,
                        "name": tool.get("name"),
                        "description": tool.get("description") or "",
                        "inputSchema": tool.get("inputSchema") or tool.get("input_schema") or {},
                    }
                )
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
        runtime=RuntimeConfig(base_url=project.runtime_base_url or "", headers=project.runtime_headers or {}),
    )

    run_row: TestRun | None = None
    if session.flow_type == FlowType.TEST_EXECUTE.value:
        run_row = TestRun(
            project_id=project.id,
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
                    data = {**data, "artifact_id": artifact_id, "gateway_ts": True}
                elif ev.event == "done":
                    session.status = "WAITING_USER" if need_user else "COMPLETED"
                    if run_row and run_row.status == "RUNNING":
                        run_row.status = "DONE"
                    db.commit()

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
        conf = score_test_case(payload, (template.fields_schema if template else None), rag_texts)
        row = TestCase(
            project_id=project_id,
            session_id=session.id,
            template_id=session.template_id,
            title=str(payload.get("title") or "未命名用例"),
            content_json=payload,
            confidence=conf,
            status="DRAFT",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    if kind == "report" and run_row:
        summary = payload.get("summary") or {}
        detail = payload.get("details") or payload
        report = TestReport(run_id=run_row.id, summary_json=summary, detail_json={"details": detail} if isinstance(detail, list) else payload, status="DONE")
        run_row.status = "DONE"
        db.add(report)
        db.commit()
        db.refresh(report)
        return report.id
    return None
