from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from langgraph.graph import END, StateGraph

from ai_test_contracts import EngineEvent, EngineRequest
from app.config import settings
from app.graphs.agent_utils import (
    critique_coverage,
    fill_gaps,
    repair_cases,
    schema_issues,
    skill_compliance,
    validate_cases,
)
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
    return {"drafts": validate_cases(req, state.get("drafts") or [])}


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


async def _draft_once(req: EngineRequest) -> dict[str, Any]:
    payload = _case_payload(req)
    if not settings.llm_enabled:
        data = mock_test_cases(req)
        data["message"] = "（Mock）" + (data.get("message") or "")
        return data
    data: dict[str, Any] = {}
    extractor = MessageStreamExtractor()
    streamed_msg = ""
    tokens: list[str] = []
    async for kind, payload_part in stream_json(
        TESTCASE_SYSTEM, json.dumps(payload, ensure_ascii=False), model=req.model
    ):
        if kind == "token":
            delta = extractor.feed(str(payload_part))
            if delta:
                streamed_msg += delta
                tokens.append(delta)
        elif kind == "result":
            data = payload_part if isinstance(payload_part, dict) else {}
    data = _normalize_testcase_data(req, data)
    data["_streamed_msg"] = streamed_msg
    data["_tokens"] = tokens
    return data


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
            "agent": "testcase_v2",
        },
    )

    yield EngineEvent(event="progress", data={"percent": 10, "step": "draft"})
    data = await _draft_once(req)
    message = data.get("message") or data.get("_streamed_msg") or "已生成测试用例"
    tokens = data.get("_tokens") or []
    if tokens:
        for delta in tokens:
            yield EngineEvent(event="token", data={"delta": delta})
    elif message:
        async for ev in _emit_text_tokens(message, chunk=12, delay=0):
            yield ev

    cases = validate_cases(req, data.get("test_cases") or [])

    # Schema repair loop (one retry)
    issues = schema_issues(cases)
    if issues:
        yield EngineEvent(
            event="progress",
            data={"percent": 35, "step": "schema_repair", "detail": {"issues": issues}},
        )
        cases = await repair_cases(req, cases, issues)
        issues = schema_issues(cases)

    # Coverage critique + gap fill
    yield EngineEvent(event="progress", data={"percent": 55, "step": "critique"})
    critique = critique_coverage(req, cases)
    if not critique.get("ok"):
        yield EngineEvent(
            event="progress",
            data={"percent": 70, "step": "gap_fill", "detail": critique},
        )
        cases = await fill_gaps(req, cases, critique)
        critique = critique_coverage(req, cases)

    compliance = skill_compliance(req, cases, "test_case")
    yield EngineEvent(
        event="progress",
        data={"percent": 90, "step": "skill_check", "detail": compliance},
    )

    note_bits = [message]
    if issues:
        note_bits.append(f"仍有 {len(issues)} 条用例字段不完整，已标记 _schema_missing。")
    if critique.get("uncovered_count"):
        note_bits.append(f"覆盖缺口约 {critique['uncovered_count']} 个测试点。")
    if compliance.get("missed"):
        note_bits.append("Skill 可能未完全遵守：" + "、".join(compliance["missed"]))
    elif compliance.get("followed"):
        note_bits.append("Skill 检查通过：" + "、".join(compliance["followed"]))
    final_msg = " ".join(note_bits)

    yield EngineEvent(
        event="message",
        data={
            "content": final_msg,
            "critique": critique,
            "skill_compliance": compliance,
            "schema_issues": issues,
        },
    )
    for tc in cases:
        payload = {**tc, "_skill_compliance": compliance, "_critique": {"uncovered_count": critique.get("uncovered_count")}}
        yield EngineEvent(event="artifact", data={"kind": "test_case", "payload": payload})
    if data.get("need_user"):
        yield EngineEvent(event="ask_user", data={"questions": data.get("questions") or []})
    yield EngineEvent(
        event="done",
        data={
            "finish_reason": "stop",
            "usage": {},
            "critique": critique,
            "skill_compliance": compliance,
        },
    )
