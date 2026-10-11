from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from langgraph.graph import END, StateGraph

from ai_test_contracts import EngineEvent, EngineRequest
from app.config import settings
from app.graphs.mock import mock_test_cases
from app.graphs.state import GraphState, req_from_state
from app.llm.provider import LlmError, MessageStreamExtractor, complete_json, resolve_api_model, stream_json
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
    payload = _case_payload(req)
    if not settings.llm_enabled:
        data = mock_test_cases(req)
        data["message"] = "（Mock）" + (data.get("message") or "")
    else:
        data = await complete_json(TESTCASE_SYSTEM, json.dumps(payload, ensure_ascii=False), model=req.model)
        data = _normalize_testcase_data(req, data)
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


def _case_payload(req: EngineRequest) -> dict[str, Any]:
    return {
        "messages": [m.model_dump() for m in req.messages],
        "context_chunks": [c.model_dump() for c in req.context_chunks],
        "template": req.template.model_dump(by_alias=True) if req.template else {},
        "artifacts": req.artifacts,
    }


def _normalize_testcase_data(req: EngineRequest, data: dict[str, Any]) -> dict[str, Any]:
    cases = data.get("test_cases") or []
    if not cases and not data.get("need_user") and not data.get("message"):
        if settings.llm_fallback_mock:
            return mock_test_cases(req)
        raise LlmError("DeepSeek 未返回 test_cases，请检查模型输出")
    if not cases and data.get("message") and "need_user" not in data:
        data["need_user"] = True
    return data


async def _emit_text_tokens(text: str, *, chunk: int = 8, delay: float = 0.01) -> AsyncIterator[EngineEvent]:
    for i in range(0, len(text), chunk):
        yield EngineEvent(event="token", data={"delta": text[i : i + chunk]})
        if delay:
            await asyncio.sleep(delay)


def _validate_cases(req: EngineRequest, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    required = []
    if req.template and isinstance(req.template.fields_schema, dict):
        required = req.template.fields_schema.get("required") or []
    drafts = []
    for case in cases:
        missing = [k for k in required if not case.get(k)]
        if missing:
            case = {**case, "_schema_missing": missing}
        drafts.append(case)
    return drafts


async def _draft_stream(state: GraphState) -> AsyncIterator[EngineEvent]:
    req = req_from_state(state)
    payload = _case_payload(req)

    if not settings.llm_enabled:
        data = mock_test_cases(req)
        data["message"] = "（Mock）" + (data.get("message") or "")
        message = data.get("message") or "已生成测试用例"
        async for ev in _emit_text_tokens(message):
            yield ev
    else:
        extractor = MessageStreamExtractor()
        streamed_msg = ""
        data: dict[str, Any] = {}
        async for kind, payload_part in stream_json(
            TESTCASE_SYSTEM, json.dumps(payload, ensure_ascii=False), model=req.model
        ):
            if kind == "token":
                delta = extractor.feed(str(payload_part))
                if delta:
                    streamed_msg += delta
                    yield EngineEvent(event="token", data={"delta": delta})
            elif kind == "result":
                data = payload_part if isinstance(payload_part, dict) else {}
        data = _normalize_testcase_data(req, data)
        message = data.get("message") or streamed_msg or "已生成测试用例"
        if not streamed_msg and message:
            async for ev in _emit_text_tokens(message, chunk=12, delay=0):
                yield ev

    message = data.get("message") or "已生成测试用例"
    cases = _validate_cases(req, data.get("test_cases") or [])
    yield EngineEvent(event="message", data={"content": message})
    for tc in cases:
        yield EngineEvent(event="artifact", data={"kind": "test_case", "payload": tc})
    if data.get("need_user"):
        yield EngineEvent(event="ask_user", data={"questions": data.get("questions") or []})


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
    state: GraphState = {"request": req.model_dump(mode="json")}
    state.update(await _bind_template(state))
    async for ev in _draft_stream(state):
        yield ev
    yield EngineEvent(event="done", data={"finish_reason": "stop", "usage": {}})
