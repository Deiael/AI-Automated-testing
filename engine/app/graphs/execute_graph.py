from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

import httpx
from langgraph.graph import END, StateGraph

from ai_test_contracts import EngineEvent, EngineRequest
from app.config import settings
from app.graphs.http_exec import run_step, seed_variables, substitute
from app.graphs.mock import mock_execute_plan
from app.graphs.state import GraphState, req_from_state
from app.llm.provider import LlmError, MessageStreamExtractor, complete_json, resolve_api_model, stream_json
from app.mcp_client import McpError, call_tool, resolve_server
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


async def _run_mcp_hooks(
    hooks: list[dict[str, Any]],
    *,
    servers: list[dict[str, Any]],
    variables: dict[str, Any],
    phase: str,
    case_title: str | None,
) -> list[dict[str, Any]]:
    results = []
    for hook in hooks or []:
        if not isinstance(hook, dict):
            continue
        tool = str(hook.get("tool") or hook.get("name") or "").strip()
        if not tool:
            continue
        srv = resolve_server(servers, hook)
        rendered_args = substitute(hook.get("arguments") or {}, variables)
        entry: dict[str, Any] = {
            "phase": phase,
            "case_title": case_title,
            "tool": tool,
            "server_id": (srv or {}).get("id") or hook.get("server_id"),
            "server_name": (srv or {}).get("name") or hook.get("server_name"),
            "arguments": rendered_args,
        }
        if not srv or not srv.get("url"):
            entry.update({"ok": False, "error": "MCP server not found or url empty"})
            results.append(entry)
            continue
        try:
            result = await call_tool(
                transport=str(srv.get("transport") or "http"),
                url=str(srv.get("url") or ""),
                tool_name=tool,
                arguments=rendered_args if isinstance(rendered_args, dict) else {},
                headers=srv.get("headers") or {},
            )
            entry.update({"ok": True, "result": result})
            # optional extract map: {"as": "otp", "from": "result.text"} — store whole result under as
            as_name = hook.get("as") or hook.get("save_as")
            if as_name:
                variables[str(as_name)] = result
                if isinstance(result, dict):
                    # common MCP content shape
                    content = result.get("content")
                    if isinstance(content, list) and content:
                        first = content[0]
                        if isinstance(first, dict) and "text" in first:
                            variables[str(as_name)] = first.get("text")
            results.append(entry)
        except McpError as exc:
            entry.update({"ok": False, "error": str(exc)})
            results.append(entry)
        except Exception as exc:  # noqa: BLE001
            entry.update({"ok": False, "error": str(exc)})
            results.append(entry)
    return results


async def _call_http(state: GraphState) -> dict[str, Any]:
    req = req_from_state(state)
    runtime = req.runtime.model_dump()
    variables = seed_variables(runtime)
    servers = req.artifacts.get("mcp_servers") or []
    # also allow resolving from mcp_tools urls
    if not servers:
        seen = {}
        for t in req.artifacts.get("mcp_tools") or []:
            sid = t.get("server_id") or t.get("server_name")
            if sid and sid not in seen and t.get("url"):
                seen[sid] = {
                    "id": t.get("server_id"),
                    "name": t.get("server_name"),
                    "transport": t.get("transport") or "http",
                    "url": t.get("url"),
                    "headers": t.get("headers") or {},
                }
        servers = list(seen.values())

    results: list[dict[str, Any]] = []
    mcp_log: list[dict[str, Any]] = []
    timeout = httpx.Timeout(30.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for step in state.get("drafts") or []:
            before = step.get("mcp_before") or []
            after = step.get("mcp_after") or []
            if before:
                mcp_log.extend(
                    await _run_mcp_hooks(
                        before,
                        servers=servers,
                        variables=variables,
                        phase="before",
                        case_title=step.get("case_title"),
                    )
                )
            if str(step.get("type") or "").lower() == "mcp":
                mcp_log.extend(
                    await _run_mcp_hooks(
                        [step],
                        servers=servers,
                        variables=variables,
                        phase="step",
                        case_title=step.get("case_title"),
                    )
                )
                continue
            item = await run_step(client, step, runtime=runtime, variables=variables)
            variables.update(item.get("extracted") or {})
            if after:
                after_res = await _run_mcp_hooks(
                    after,
                    servers=servers,
                    variables=variables,
                    phase="after",
                    case_title=step.get("case_title"),
                )
                mcp_log.extend(after_res)
                item["mcp_after"] = after_res
            if before:
                item["mcp_before"] = [m for m in mcp_log if m.get("phase") == "before" and m.get("case_title") == step.get("case_title")]
            results.append(item)
    return {"progress": results, "variables": variables, "mcp_log": mcp_log}


async def _summarize(state: GraphState) -> dict[str, Any]:
    details = state.get("progress") or []
    total = len(details)
    passed = sum(1 for d in details if d.get("ok"))
    failed_titles = [d.get("case_title") for d in details if not d.get("ok")]
    elapsed = sum(int(d.get("time_ms") or 0) for d in details)
    mcp_log = state.get("mcp_log") or []
    mcp_fail = sum(1 for m in mcp_log if not m.get("ok"))
    report = {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "time_ms": elapsed,
            "failed_titles": failed_titles,
            "mcp_calls": len(mcp_log),
            "mcp_failed": mcp_fail,
        },
        "details": details,
        "variables": state.get("variables") or {},
        "mcp_log": mcp_log,
    }
    msg = f"执行完成：通过 {passed}/{total}，耗时 {elapsed}ms"
    if failed_titles:
        msg += "；失败：" + "、".join(str(t) for t in failed_titles[:5] if t)
    if mcp_log:
        msg += f"；MCP 调用 {len(mcp_log)} 次（失败 {mcp_fail}）"
    return {"report": report, "message": msg}


async def _emit_text_tokens(text: str, *, chunk: int = 8, delay: float = 0.01) -> AsyncIterator[EngineEvent]:
    for i in range(0, len(text), chunk):
        yield EngineEvent(event="token", data={"delta": text[i : i + chunk]})
        if delay:
            await asyncio.sleep(delay)


async def _plan_stream(state: GraphState) -> AsyncIterator[EngineEvent]:
    req = req_from_state(state)
    payload = json.dumps({"artifacts": req.artifacts, "runtime": req.runtime.model_dump()}, ensure_ascii=False)
    data: dict[str, Any] = {}

    if not settings.llm_enabled:
        data = mock_execute_plan(req)
        data["message"] = "（Mock）" + (data.get("message") or "")
        message = data.get("message") or "开始执行"
        async for ev in _emit_text_tokens(message):
            yield ev
    else:
        extractor = MessageStreamExtractor()
        streamed_msg = ""
        async for kind, part in stream_json(EXECUTE_SYSTEM, payload, model=req.model):
            if kind == "token":
                delta = extractor.feed(str(part))
                if delta:
                    streamed_msg += delta
                    yield EngineEvent(event="token", data={"delta": delta})
            elif kind == "result":
                data = part if isinstance(part, dict) else {}
        if not data.get("plan"):
            if settings.llm_fallback_mock:
                data = mock_execute_plan(req)
            else:
                raise LlmError("DeepSeek 未返回执行 plan")
        message = data.get("message") or streamed_msg or "开始执行"
        if not streamed_msg and message:
            async for ev in _emit_text_tokens(message, chunk=12, delay=0):
                yield ev

    plan = _steps_from_cases(req) or _attach_case_meta(req, data.get("plan") or [])
    message = data.get("message") or "开始执行"
    state["drafts"] = plan
    state["message"] = message
    yield EngineEvent(event="message", data={"content": message})


def _steps_from_cases(req: EngineRequest) -> list[dict[str, Any]]:
    cases = req.artifacts.get("test_cases") or []
    if not cases:
        return []
    base = (req.runtime.base_url or "").rstrip("/")
    steps: list[dict[str, Any]] = []
    for c in cases:
        path = c.get("path") or "/"
        url = c.get("url") or f"{base}{path if str(path).startswith('/') else '/' + path}"
        steps.append(
            {
                "case_id": c.get("id"),
                "case_title": c.get("title"),
                "confidence": c.get("confidence"),
                "method": c.get("method") or "GET",
                "path": path,
                "url": url,
                "headers": c.get("headers") or {},
                "query": c.get("query") or {},
                "body": c.get("body"),
                "assert": c.get("assert") or {"status_code": 200},
                "extract": c.get("extract") or [],
                "mcp_before": c.get("mcp_before") or [],
                "mcp_after": c.get("mcp_after") or [],
            }
        )
    return steps


def _attach_case_meta(req: EngineRequest, plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases = req.artifacts.get("test_cases") or []
    by_id = {c.get("id"): c for c in cases if c.get("id")}
    by_title = {c.get("title"): c for c in cases if c.get("title")}
    out: list[dict[str, Any]] = []
    for i, step in enumerate(plan):
        src = by_id.get(step.get("case_id")) or by_title.get(step.get("case_title"))
        if not src and i < len(cases):
            src = cases[i]
        if src:
            step = {
                **step,
                "case_id": src.get("id") or step.get("case_id"),
                "case_title": step.get("case_title") or src.get("title"),
                "confidence": src.get("confidence") if src.get("confidence") is not None else step.get("confidence"),
                "method": src.get("method") or step.get("method"),
                "path": src.get("path") or step.get("path"),
                "headers": {**(step.get("headers") or {}), **(src.get("headers") or {})},
                "query": src.get("query") or step.get("query") or {},
                "body": src.get("body") if "body" in src else step.get("body"),
                "assert": src.get("assert") or step.get("assert") or {},
                "extract": src.get("extract") or step.get("extract") or [],
                "mcp_before": src.get("mcp_before") or step.get("mcp_before") or [],
                "mcp_after": src.get("mcp_after") or step.get("mcp_after") or [],
            }
        out.append(step)
    return out


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
            "agent": "execute_v2",
        },
    )

    state: GraphState = {"request": req.model_dump(mode="json")}
    async for ev in _plan_stream(state):
        yield ev
    yield EngineEvent(event="progress", data={"percent": 20, "step": "plan"})

    state.update(await _call_http(state))
    for i, item in enumerate(state.get("progress") or []):
        pct = 20 + int(60 * (i + 1) / max(1, len(state.get("progress") or [])))
        yield EngineEvent(event="progress", data={"percent": pct, "step": "call_http", "detail": item})
    for m in state.get("mcp_log") or []:
        yield EngineEvent(event="progress", data={"percent": 85, "step": "mcp", "detail": m})

    state.update(await _summarize(state))
    yield EngineEvent(event="progress", data={"percent": 100, "step": "done"})

    message = state.get("message") or ""
    async for ev in _emit_text_tokens(message, chunk=12, delay=0):
        yield ev
    yield EngineEvent(event="message", data={"content": message})
    yield EngineEvent(event="artifact", data={"kind": "report", "payload": state.get("report") or {}})
    yield EngineEvent(event="done", data={"finish_reason": "stop", "usage": {}})
