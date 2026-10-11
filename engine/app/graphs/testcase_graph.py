from __future__ import annotations

import json
from typing import Any, AsyncIterator

from langgraph.graph import END, StateGraph

from ai_test_contracts import EngineEvent, EngineRequest
from app.config import settings
from app.graphs.mock import mock_test_cases
from app.graphs.state import GraphState, req_from_state
from app.llm.provider import LlmError, complete_json, resolve_api_model
from app.prompts import TESTCASE_SYSTEM


def build_testcase_graph():
    g = StateGraph(GraphState)
    g.add_node("bind_template", _bind_template)
    g.add_node("draft", _draft)
    g.add_node("validate", _validate)
    g.set_entry_point("bind_template")
    g.add_edge("bind_template", "draft")
    g.add_edge("draft", "validate")
    g.add_edge("validate", END)
    return g.compile()


async def _bind_template(state: GraphState) -> dict[str, Any]:
    req = req_from_state(state)
    name = req.template.name if req.template else "default"
    return {"analysis": f"template={name}"}


async def _draft(state: GraphState) -> dict[str, Any]:
    req = req_from_state(state)
    payload = {
        "messages": [m.model_dump() for m in req.messages],
        "context_chunks": [c.model_dump() for c in req.context_chunks],
        "template": req.template.model_dump(by_alias=True) if req.template else {},
        "artifacts": req.artifacts,
    }
    if not settings.llm_enabled:
        data = mock_test_cases(req)
        data["message"] = "（Mock）" + (data.get("message") or "")
    else:
        data = await complete_json(TESTCASE_SYSTEM, json.dumps(payload, ensure_ascii=False), model=req.model)
        cases = data.get("test_cases") or []
        if not cases and not data.get("need_user") and not data.get("message"):
            if settings.llm_fallback_mock:
                data = mock_test_cases(req)
            else:
                raise LlmError("DeepSeek 未返回 test_cases，请检查模型输出")
        # 闲聊/追问时允许只返回 message，不强制产物
        if not cases and data.get("message") and "need_user" not in data:
            data["need_user"] = True
    return {
        "drafts": data.get("test_cases") or [],
        "message": data.get("message") or "已生成测试用例",
        "need_user": bool(data.get("need_user")),
        "questions": data.get("questions") or [],
    }


async def _validate(state: GraphState) -> dict[str, Any]:
    req = req_from_state(state)
    required = []
    if req.template and isinstance(req.template.fields_schema, dict):
        required = req.template.fields_schema.get("required") or []
    drafts = []
    for case in state.get("drafts") or []:
        missing = [k for k in required if not case.get(k)]
        if missing:
            case = {**case, "_schema_missing": missing}
        drafts.append(case)
    return {"drafts": drafts}


async def run_testcase_stream(req: EngineRequest) -> AsyncIterator[EngineEvent]:
    api_model = resolve_api_model(req.model)
    yield EngineEvent(
        event="meta",
        data={
            "request_id": req.request_id,
            "flow": req.flow.value,
            "model": api_model,
            "llm_enabled": settings.llm_enabled,
            "provider": "deepseek/openai-compatible",
        },
    )
    graph = build_testcase_graph()
    result = await graph.ainvoke({"request": req.model_dump(mode="json")})

    message = result.get("message") or ""
    for i in range(0, len(message), 12):
        yield EngineEvent(event="token", data={"delta": message[i : i + 12]})
    yield EngineEvent(event="message", data={"content": message})

    for tc in result.get("drafts") or []:
        yield EngineEvent(event="artifact", data={"kind": "test_case", "payload": tc})

    if result.get("need_user"):
        yield EngineEvent(event="ask_user", data={"questions": result.get("questions") or []})

    yield EngineEvent(event="done", data={"finish_reason": "stop", "usage": {}})
