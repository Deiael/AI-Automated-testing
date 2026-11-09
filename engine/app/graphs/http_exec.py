from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.parse import urljoin

import httpx

_VAR = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")


def substitute(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, str):
        def repl(m: re.Match[str]) -> str:
            key = m.group(1)
            if key in variables and variables[key] is not None:
                return str(variables[key])
            return m.group(0)

        return _VAR.sub(repl, value)
    if isinstance(value, list):
        return [substitute(v, variables) for v in value]
    if isinstance(value, dict):
        return {k: substitute(v, variables) for k, v in value.items()}
    return value


def json_get(data: Any, path: str) -> Any:
    if not path or path in ("$", "$.") :
        return data
    raw = path.strip()
    if raw.startswith("$."):
        raw = raw[2:]
    elif raw.startswith("$"):
        raw = raw[1:]
        if raw.startswith("."):
            raw = raw[1:]
    if not raw:
        return data
    cur: Any = data
    token = re.compile(r"\.?([^[.\]]+)|\[(\d+)\]")
    pos = 0
    for m in token.finditer(raw):
        if m.start() != pos:
            return None
        pos = m.end()
        key, idx = m.group(1), m.group(2)
        if idx is not None:
            if not isinstance(cur, list):
                return None
            i = int(idx)
            if i >= len(cur):
                return None
            cur = cur[i]
        else:
            if not isinstance(cur, dict) or key not in cur:
                return None
            cur = cur[key]
    if pos != len(raw):
        return None
    return cur


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def eval_assertions(
    *,
    expect: dict[str, Any] | None,
    status_code: int,
    body_text: str,
    body_json: Any,
    time_ms: int,
) -> list[dict[str, Any]]:
    expect = expect or {}
    results: list[dict[str, Any]] = []

    if "status_code" in expect and expect["status_code"] not in (None, ""):
        want = int(expect["status_code"])
        ok = status_code == want
        results.append(
            {
                "name": "status_code",
                "ok": ok,
                "expected": want,
                "actual": status_code,
                "message": None if ok else f"期望状态码 {want}，实际 {status_code}",
            }
        )

    if expect.get("status_code_in"):
        want_list = [int(x) for x in _as_list(expect.get("status_code_in")) if str(x).strip() != ""]
        ok = status_code in want_list
        results.append(
            {
                "name": "status_code_in",
                "ok": ok,
                "expected": want_list,
                "actual": status_code,
                "message": None if ok else f"期望状态码 ∈ {want_list}，实际 {status_code}",
            }
        )

    if expect.get("status_code_gte") not in (None, ""):
        want = int(expect["status_code_gte"])
        ok = status_code >= want
        results.append(
            {
                "name": "status_code_gte",
                "ok": ok,
                "expected": want,
                "actual": status_code,
                "message": None if ok else f"期望状态码 ≥ {want}，实际 {status_code}",
            }
        )

    if expect.get("status_code_lt") not in (None, ""):
        want = int(expect["status_code_lt"])
        ok = status_code < want
        results.append(
            {
                "name": "status_code_lt",
                "ok": ok,
                "expected": want,
                "actual": status_code,
                "message": None if ok else f"期望状态码 < {want}，实际 {status_code}",
            }
        )

    if "max_ms" in expect and expect["max_ms"] not in (None, ""):
        want = int(expect["max_ms"])
        ok = time_ms <= want
        results.append(
            {
                "name": "max_ms",
                "ok": ok,
                "expected": want,
                "actual": time_ms,
                "message": None if ok else f"耗时 {time_ms}ms 超过 {want}ms",
            }
        )

    for needle in _as_list(expect.get("body_contains")):
        text = str(needle)
        if not text:
            continue
        ok = text in (body_text or "")
        results.append(
            {
                "name": "body_contains",
                "ok": ok,
                "expected": text,
                "actual": (body_text or "")[:200],
                "message": None if ok else f"响应未包含「{text}」",
            }
        )

    jsonpath = expect.get("jsonpath") or expect.get("json_equals")
    pairs: list[tuple[str, Any]] = []
    if isinstance(jsonpath, dict):
        pairs = list(jsonpath.items())
    elif isinstance(jsonpath, list):
        for item in jsonpath:
            if isinstance(item, dict) and item.get("path"):
                pairs.append((str(item["path"]), item.get("equals", item.get("value"))))
    for path, want in pairs:
        actual = json_get(body_json, path) if body_json is not None else None
        ok = actual == want
        results.append(
            {
                "name": "jsonpath",
                "ok": ok,
                "expected": {"path": path, "equals": want},
                "actual": actual,
                "message": None if ok else f"{path} 期望 {want!r}，实际 {actual!r}",
            }
        )

    if not results:
        results.append(
            {
                "name": "status_code",
                "ok": 200 <= status_code < 400,
                "expected": "2xx/3xx",
                "actual": status_code,
                "message": None if 200 <= status_code < 400 else f"HTTP {status_code}",
            }
        )
    return results


def extract_vars(extract: Any, body_json: Any, status_code: int) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in _as_list(extract):
        if not isinstance(item, dict):
            continue
        name = str(item.get("as") or item.get("name") or "").strip()
        path = str(item.get("path") or "").strip()
        if not name or not path:
            continue
        if path in ("status_code", "$.status_code"):
            out[name] = status_code
        else:
            out[name] = json_get(body_json, path)
    return out


def build_url(base_url: str, path: str, explicit: str | None = None) -> str:
    if explicit and str(explicit).strip():
        url = str(explicit).strip()
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return urljoin(base_url.rstrip("/") + "/", url.lstrip("/"))
    path = path or "/"
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


async def run_step(
    client: httpx.AsyncClient,
    step: dict[str, Any],
    *,
    runtime: dict[str, Any],
    variables: dict[str, Any],
) -> dict[str, Any]:
    vars_now = dict(variables)
    rendered = substitute(step, vars_now)
    method = str(rendered.get("method") or "GET").upper()
    base = str(runtime.get("base_url") or "")
    url = build_url(base, str(rendered.get("path") or "/"), rendered.get("url"))
    headers = {**(runtime.get("headers") or {}), **(rendered.get("headers") or {})}
    headers = {str(k): str(v) for k, v in headers.items() if v is not None}
    query = rendered.get("query") or rendered.get("params") or {}
    if not isinstance(query, dict):
        query = {}
    body = rendered.get("body")
    expect = rendered.get("assert") or {}
    if not isinstance(expect, dict):
        expect = {}

    req_snap = {"method": method, "url": url, "headers": headers, "query": query, "body": body}
    started = time.perf_counter()
    try:
        kwargs: dict[str, Any] = {"headers": headers, "params": query}
        if method not in ("GET", "HEAD", "DELETE") or body not in (None, ""):
            if isinstance(body, (dict, list)):
                kwargs["json"] = body
            elif body not in (None, ""):
                kwargs["content"] = str(body).encode("utf-8")
        resp = await client.request(method, url, **kwargs)
        time_ms = int((time.perf_counter() - started) * 1000)
        text = resp.text or ""
        try:
            body_json: Any = resp.json()
        except Exception:  # noqa: BLE001
            body_json = None
        assertions = eval_assertions(
            expect=expect,
            status_code=resp.status_code,
            body_text=text,
            body_json=body_json,
            time_ms=time_ms,
        )
        extracted = extract_vars(rendered.get("extract"), body_json, resp.status_code)
        vars_now.update({k: v for k, v in extracted.items() if v is not None})
        failed = [a["name"] for a in assertions if not a.get("ok")]
        return {
            "case_id": step.get("case_id"),
            "case_title": step.get("case_title") or rendered.get("title"),
            "confidence": step.get("confidence"),
            "ok": not failed,
            "time_ms": time_ms,
            "status_code": resp.status_code,
            "error": None,
            "failed": failed,
            "request": req_snap,
            "response": {
                "status_code": resp.status_code,
                "headers": dict(list(resp.headers.items())[:20]),
                "body_preview": text[:2000],
                "json": body_json if not isinstance(body_json, (dict, list)) or _small(body_json) else None,
            },
            "assertions": assertions,
            "extracted": extracted,
            "variables_after": {k: vars_now[k] for k in list(vars_now)[-30:]},
            "url": url,
            "method": method,
            "body_preview": text[:500],
        }
    except Exception as exc:  # noqa: BLE001
        time_ms = int((time.perf_counter() - started) * 1000)
        return {
            "case_id": step.get("case_id"),
            "case_title": step.get("case_title") or step.get("title"),
            "confidence": step.get("confidence"),
            "ok": False,
            "time_ms": time_ms,
            "status_code": 0,
            "error": str(exc),
            "failed": ["request"],
            "request": req_snap,
            "response": {"status_code": 0, "headers": {}, "body_preview": "", "json": None},
            "assertions": [
                {
                    "name": "request",
                    "ok": False,
                    "expected": "HTTP 成功",
                    "actual": str(exc),
                    "message": str(exc),
                }
            ],
            "extracted": {},
            "variables_after": vars_now,
            "url": url,
            "method": method,
            "body_preview": "",
        }


def _small(obj: Any, limit: int = 4000) -> bool:
    try:
        return len(json.dumps(obj, ensure_ascii=False)) <= limit
    except Exception:  # noqa: BLE001
        return False


def seed_variables(runtime: dict[str, Any]) -> dict[str, Any]:
    vars_now = dict(runtime.get("variables") or {})
    if runtime.get("base_url"):
        vars_now.setdefault("base_url", runtime["base_url"])
    return vars_now
