from __future__ import annotations

import json
import re
from typing import Any

import yaml

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def parse_openapi_text(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty OpenAPI document")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("OpenAPI root must be an object")
    return data


def extract_operations(spec: dict[str, Any]) -> list[dict[str, Any]]:
    paths = spec.get("paths") or {}
    if not isinstance(paths, dict):
        return []
    ops: list[dict[str, Any]] = []
    for path, item in paths.items():
        if not isinstance(item, dict):
            continue
        shared_params = item.get("parameters") if isinstance(item.get("parameters"), list) else []
        for method, op in item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(op, dict):
                continue
            params = list(shared_params)
            if isinstance(op.get("parameters"), list):
                params.extend(op["parameters"])
            status_codes = []
            responses = op.get("responses") or {}
            if isinstance(responses, dict):
                status_codes = [str(k) for k in responses.keys()]
            req_body = op.get("requestBody") if isinstance(op.get("requestBody"), dict) else None
            sample_body = _sample_from_request_body(req_body) if req_body else None
            ops.append(
                {
                    "operation_id": op.get("operationId") or f"{method.upper()} {path}",
                    "method": method.upper(),
                    "path": str(path),
                    "summary": op.get("summary") or op.get("operationId") or f"{method.upper()} {path}",
                    "description": op.get("description") or "",
                    "tags": op.get("tags") if isinstance(op.get("tags"), list) else [],
                    "parameters": params,
                    "status_codes": status_codes,
                    "has_request_body": bool(req_body),
                    "sample_body": sample_body,
                    "security": op.get("security") if op.get("security") is not None else spec.get("security"),
                }
            )
    return ops


def normalize_path(path: str) -> str:
    """Collapse {param} / :param style segments for coverage matching."""
    p = str(path or "").strip() or "/"
    p = re.sub(r"\{[^}]+\}", "{}", p)
    p = re.sub(r":[A-Za-z_][A-Za-z0-9_]*", "{}", p)
    if not p.startswith("/"):
        p = "/" + p
    return p.rstrip("/") or "/"


def operation_key(method: str, path: str) -> str:
    return f"{str(method or 'GET').upper()} {normalize_path(path)}"


def build_point_and_cases(
    op: dict[str, Any],
    *,
    project_id: str,
    pipeline_id: str | None,
    confirm: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    method = op["method"]
    path = op["path"]
    title = str(op.get("summary") or op["operation_id"])
    status = "CONFIRMED" if confirm else "DRAFT"
    expected_ok = _preferred_success(op.get("status_codes") or [])
    point = {
        "project_id": project_id,
        "pipeline_id": pipeline_id,
        "title": f"[API] {method} {path}",
        "status": status,
        "content_json": {
            "source": "openapi",
            "operation_id": op.get("operation_id"),
            "method": method,
            "path": path,
            "key": operation_key(method, path),
            "summary": op.get("summary"),
            "description": op.get("description"),
            "tags": op.get("tags") or [],
            "status_codes": op.get("status_codes") or [],
        },
    }
    cases: list[dict[str, Any]] = []
    happy = {
        "title": f"{title} · 正向",
        "status": status,
        "content_json": {
            "source": "openapi",
            "operation_key": operation_key(method, path),
            "method": method,
            "path": path,
            "precondition": "接口可用；鉴权与环境变量已配置" if op.get("security") else "接口可用",
            "steps": [
                {"action": f"调用 {method} {path}", "data": op.get("sample_body") or {}},
            ],
            "expected": f"返回 HTTP {expected_ok}",
            "priority": "P1",
            "headers": {},
            "body": op.get("sample_body") if method in {"POST", "PUT", "PATCH"} else None,
            "assert": {"status_code": expected_ok},
            "extract": [],
        },
    }
    cases.append(happy)
    # Negative / auth case when security is declared
    if op.get("security"):
        cases.append(
            {
                "title": f"{title} · 未授权",
                "status": status,
                "content_json": {
                    "source": "openapi",
                    "operation_key": operation_key(method, path),
                    "method": method,
                    "path": path,
                    "precondition": "不携带有效鉴权",
                    "steps": [{"action": f"无鉴权调用 {method} {path}", "data": {}}],
                    "expected": "返回 401 或 403",
                    "priority": "P2",
                    "headers": {},
                    "body": None,
                    "assert": {"status_code_in": [401, 403]},
                    "extract": [],
                },
            }
        )
    # Missing path param / bad request style when path has params
    if "{" in path:
        bad_path = re.sub(r"\{[^}]+\}", "invalid", path)
        cases.append(
            {
                "title": f"{title} · 非法路径参数",
                "status": status,
                "content_json": {
                    "source": "openapi",
                    "operation_key": operation_key(method, path),
                    "method": method,
                    "path": bad_path,
                    "precondition": "使用非法路径参数",
                    "steps": [{"action": f"调用 {method} {bad_path}", "data": {}}],
                    "expected": "返回 4xx",
                    "priority": "P2",
                    "headers": {},
                    "body": None,
                    "assert": {"status_code_gte": 400, "status_code_lt": 500},
                    "extract": [],
                },
            }
        )
    return point, cases


def _preferred_success(codes: list[str]) -> int:
    for prefer in ("200", "201", "204", "202"):
        if prefer in codes:
            return int(prefer)
    for c in codes:
        if str(c).isdigit() and str(c).startswith("2"):
            return int(c)
    return 200


def _sample_from_request_body(body: dict[str, Any]) -> Any:
    content = body.get("content") if isinstance(body.get("content"), dict) else {}
    for mime in ("application/json", "application/x-www-form-urlencoded", "multipart/form-data"):
        media = content.get(mime)
        if not isinstance(media, dict):
            continue
        if "example" in media:
            return media["example"]
        examples = media.get("examples")
        if isinstance(examples, dict) and examples:
            first = next(iter(examples.values()))
            if isinstance(first, dict) and "value" in first:
                return first["value"]
        schema = media.get("schema")
        if isinstance(schema, dict):
            if "example" in schema:
                return schema["example"]
            return _sample_from_schema(schema)
    return None


def _sample_from_schema(schema: dict[str, Any]) -> Any:
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    t = schema.get("type")
    if t == "object" or "properties" in schema:
        props = schema.get("properties") or {}
        out = {}
        for k, v in props.items():
            if isinstance(v, dict):
                out[k] = _sample_from_schema(v)
        return out
    if t == "array":
        items = schema.get("items") if isinstance(schema.get("items"), dict) else {}
        return [_sample_from_schema(items)] if items else []
    if t == "integer":
        return 1
    if t == "number":
        return 1.0
    if t == "boolean":
        return True
    if "enum" in schema and isinstance(schema["enum"], list) and schema["enum"]:
        return schema["enum"][0]
    return "string"
