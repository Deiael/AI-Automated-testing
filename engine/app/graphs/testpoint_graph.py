from __future__ import annotations

import json
from typing import Any, AsyncIterator

from langgraph.graph import END, StateGraph

from ai_test_contracts import EngineEvent, EngineRequest
from app.config import settings
from app.graphs.mock import mock_test_points
from app.graphs.state import GraphState, req_from_state
from app.llm.provider import LlmError, complete_json, resolve_api_model
from app.prompts import TESTPOINT_SYSTEM


def build_testpoint_graph():
    g = StateGraph(GraphState)
    g.add_node("analyze", _analyze)
    g.add_node("draft", _draft)
    g.add_node("finalize", _finalize)
    g.set_entry_point("analyze")
    g.add_edge("analyze", "draft")
    g.add_edge("draft", "finalize")
    g.add_edge("finalize", END)
    return g.compile()


async def _analyze(state: GraphState) -> dict[str, Any]:
    req = req_from_state(state)
    ctx = "\n".join(f"- {c.title}: {c.text[:200]}" for c in req.context_chunks)
    return {"analysis": f"messages={len(req.messages)}; rag_chunks={len(req.context_chunks)}; ctx={ctx[:200]}"}


async def _draft(state: GraphState) -> dict[str, Any]:
    req = req_from_state(state)
    user_blob = json.dumps(
        {
            "messages": [m.model_dump() for m in req.messages],
            "context_chunks": [c.model_dump() for c in req.context_chunks],
            "analysis": state.get("analysis", ""),
        },
        ensure_ascii=False,
    )
    if not settings.llm_enabled:
        data = mock_test_points(req)
        data["message"] = "（Mock）" + (data.get("message") or "")
    else:
        data = await complete_json(TESTPOINT_SYSTEM, user_blob, model=req.model)
        points = data.get("test_points") or []
        if not points and not data.get("need_user") and not data.get("message"):
            if settings.llm_fallback_mock:
                data = mock_test_points(req)
            else:
                raise LlmError("DeepSeek 未返回 test_points，请检查模型输出")
        if not points and data.get("message") and "need_user" not in data:
            data["need_user"] = True
    return {
        "drafts": data.get("test_points") or [],
        "message": data.get("message") or "已生成测试点",
        "need_user": bool(data.get("need_user")),
        "questions": data.get("questions") or [],
    }


async def _finalize(state: GraphState) -> dict[str, Any]:
    return {}


async def run_testpoint_stream(req: EngineRequest) -> AsyncIterator[EngineEvent]:
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
    graph = build_testpoint_graph()
    result = await graph.ainvoke({"request": req.model_dump(mode="json")})

    message = result.get("message") or ""
    for i in range(0, len(message), 12):
        yield EngineEvent(event="token", data={"delta": message[i : i + 12]})
    yield EngineEvent(event="message", data={"content": message})

    for tp in result.get("drafts") or []:
        yield EngineEvent(event="artifact", data={"kind": "test_point", "payload": tp})

    if result.get("need_user"):
        yield EngineEvent(event="ask_user", data={"questions": result.get("questions") or []})

    yield EngineEvent(event="done", data={"finish_reason": "stop", "usage": {}})
