from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from langgraph.graph import END, StateGraph

from ai_test_contracts import EngineEvent, EngineRequest
from app.config import settings
from app.graphs.mock import mock_test_points
from app.graphs.state import GraphState, req_from_state
from app.llm.provider import LlmError, MessageStreamExtractor, complete_json, resolve_api_model, stream_json
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
    user_blob = _user_blob(req, state)
    if not settings.llm_enabled:
        data = mock_test_points(req)
        data["message"] = "（Mock）" + (data.get("message") or "")
    else:
        data = await complete_json(TESTPOINT_SYSTEM, user_blob, model=req.model)
        data = _normalize_testpoint_data(req, data)
    return {
        "drafts": data.get("test_points") or [],
        "message": data.get("message") or "已生成测试点",
        "need_user": bool(data.get("need_user")),
        "questions": data.get("questions") or [],
    }


async def _finalize(state: GraphState) -> dict[str, Any]:
    return {}


def _user_blob(req: EngineRequest, state: GraphState) -> str:
    return json.dumps(
        {
            "messages": [m.model_dump() for m in req.messages],
            "context_chunks": [c.model_dump() for c in req.context_chunks],
            "analysis": state.get("analysis", ""),
        },
        ensure_ascii=False,
    )


def _normalize_testpoint_data(req: EngineRequest, data: dict[str, Any]) -> dict[str, Any]:
    points = data.get("test_points") or []
    if not points and not data.get("need_user") and not data.get("message"):
        if settings.llm_fallback_mock:
            return mock_test_points(req)
        raise LlmError("DeepSeek 未返回 test_points，请检查模型输出")
    if not points and data.get("message") and "need_user" not in data:
        data["need_user"] = True
    return data


async def _emit_text_tokens(text: str, *, chunk: int = 8, delay: float = 0.01) -> AsyncIterator[EngineEvent]:
    for i in range(0, len(text), chunk):
        yield EngineEvent(event="token", data={"delta": text[i : i + chunk]})
        if delay:
            await asyncio.sleep(delay)


async def _draft_stream(state: GraphState) -> AsyncIterator[EngineEvent]:
    req = req_from_state(state)
    user_blob = _user_blob(req, state)

    if not settings.llm_enabled:
        data = mock_test_points(req)
        data["message"] = "（Mock）" + (data.get("message") or "")
        message = data.get("message") or "已生成测试点"
        async for ev in _emit_text_tokens(message):
            yield ev
    else:
        extractor = MessageStreamExtractor()
        streamed_msg = ""
        data: dict[str, Any] = {}
        async for kind, payload in stream_json(TESTPOINT_SYSTEM, user_blob, model=req.model):
            if kind == "token":
                delta = extractor.feed(str(payload))
                if delta:
                    streamed_msg += delta
                    yield EngineEvent(event="token", data={"delta": delta})
            elif kind == "result":
                data = payload if isinstance(payload, dict) else {}
        data = _normalize_testpoint_data(req, data)
        message = data.get("message") or streamed_msg or "已生成测试点"
        if not streamed_msg and message:
            async for ev in _emit_text_tokens(message, chunk=12, delay=0):
                yield ev

    message = data.get("message") or "已生成测试点"
    yield EngineEvent(event="message", data={"content": message})
    for tp in data.get("test_points") or []:
        yield EngineEvent(event="artifact", data={"kind": "test_point", "payload": tp})
    if data.get("need_user"):
        yield EngineEvent(event="ask_user", data={"questions": data.get("questions") or []})


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
    state: GraphState = {"request": req.model_dump(mode="json")}
    state.update(await _analyze(state))
    async for ev in _draft_stream(state):
        yield ev
    yield EngineEvent(event="done", data={"finish_reason": "stop", "usage": {}})
