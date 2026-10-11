from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx
from langgraph.graph import END, StateGraph

from ai_test_contracts import EngineEvent, EngineRequest
from app.config import settings
from app.graphs.mock import mock_execute_plan
from app.graphs.state import GraphState, req_from_state
from app.llm.provider import LlmError, complete_json, resolve_api_model
from app.prompts import EXECUTE_SYSTEM


def build_execute_graph():
    g = StateGraph(GraphState)
    g.add_node("plan", _plan)
    g.add_node("call_http", _call_http)
    g.add_node("summarize", _summarize)
    g.set_entry_point("plan")
    g.add_edge("plan", "call_http")
    g.add_edge("call_http", "summarize")
    g.add_edge("summarize", END)
    return g.compile()


async def _plan(state: GraphState) -> dict[str, Any]:
    req = req_from_state(state)
    payload = json.dumps({"artifacts": req.artifacts, "runtime": req.runtime.model_dump()}, ensure_ascii=False)
    if not settings.llm_enabled:
        data = mock_execute_plan(req)
        data["message"] = "（Mock）" + (data.get("message") or "")
    else:
        data = await complete_json(EXECUTE_SYSTEM, payload, model=req.model)
        if not data.get("plan"):
            if settings.llm_fallback_mock:
                data = mock_execute_plan(req)
            else:
                raise LlmError("DeepSeek 未返回执行 plan")
    return {"drafts": data.get("plan") or [], "message": data.get("message") or "开始执行"}


async def _call_http(state: GraphState) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for step in state.get("drafts") or []:
            method = (step.get("method") or "GET").upper()
            url = step.get("url") or "http://127.0.0.1:9/"
            headers = step.get("headers") or {}
            body = step.get("body")
            expect = step.get("assert") or {}
            try:
                resp = await client.request(method, url, headers=headers, json=body)
                ok = True
                if "status_code" in expect:
                    ok = resp.status_code == int(expect["status_code"])
                results.append(
                    {
                        "case_title": step.get("case_title"),
                        "url": url,
                        "method": method,
                        "status_code": resp.status_code,
                        "ok": ok,
                        "body_preview": resp.text[:500],
                    }
                )
            except Exception as exc:  # noqa: BLE001
                results.append(
                    {
                        "case_title": step.get("case_title"),
                        "url": url,
                        "method": method,
                        "status_code": 0,
                        "ok": False,
                        "error": str(exc),
                    }
                )
    return {"progress": results}


async def _summarize(state: GraphState) -> dict[str, Any]:
    details = state.get("progress") or []
    total = len(details)
    passed = sum(1 for d in details if d.get("ok"))
    report = {
        "summary": {"total": total, "passed": passed, "failed": total - passed},
        "details": details,
    }
    msg = f"执行完成：通过 {passed}/{total}"
    return {"report": report, "message": msg}


async def run_execute_stream(req: EngineRequest) -> AsyncIterator[EngineEvent]:
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

    # stream progress by running nodes stepwise
    state: GraphState = {"request": req.model_dump(mode="json")}
    state.update(await _plan(state))
    yield EngineEvent(event="progress", data={"percent": 20, "step": "plan"})
    state.update(await _call_http(state))
    for i, item in enumerate(state.get("progress") or []):
        pct = 20 + int(70 * (i + 1) / max(1, len(state.get("progress") or [])))
        yield EngineEvent(event="progress", data={"percent": pct, "step": "call_http", "detail": item})
    state.update(await _summarize(state))
    yield EngineEvent(event="progress", data={"percent": 100, "step": "done"})

    message = state.get("message") or ""
    for i in range(0, len(message), 12):
        yield EngineEvent(event="token", data={"delta": message[i : i + 12]})
    yield EngineEvent(event="message", data={"content": message})
    yield EngineEvent(event="artifact", data={"kind": "report", "payload": state.get("report") or {}})
    yield EngineEvent(event="done", data={"finish_reason": "stop", "usage": {}})
