from __future__ import annotations

import json
import re
from typing import Any

from ai_test_contracts import EngineRequest
from app.config import settings
from app.llm.provider import complete_json


def required_fields(req: EngineRequest) -> list[str]:
    if req.template and isinstance(req.template.fields_schema, dict):
        return list(req.template.fields_schema.get("required") or [])
    return ["title", "steps", "expected"]


def validate_cases(req: EngineRequest, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    required = required_fields(req)
    out = []
    for case in cases:
        missing = [k for k in required if not _has(case, k)]
        row = {**case}
        if missing:
            row["_schema_missing"] = missing
        else:
            row.pop("_schema_missing", None)
        out.append(row)
    return out


def schema_issues(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"title": c.get("title") or "untitled", "missing": c.get("_schema_missing") or []}
        for c in cases
        if c.get("_schema_missing")
    ]


def critique_coverage(req: EngineRequest, cases: list[dict[str, Any]]) -> dict[str, Any]:
    points = req.artifacts.get("test_points") or []
    titles = [str(c.get("title") or "") for c in cases]
    blob = " ".join(titles).lower()
    uncovered = []
    for p in points:
        pt = str(p.get("title") or "")
        if not pt:
            continue
        tokens = [t for t in re.split(r"[\s:：\-_/]+", pt.lower()) if len(t) >= 2][:4]
        hit = any(tok in blob for tok in tokens) if tokens else pt.lower() in blob
        if not hit:
            uncovered.append({"id": p.get("id"), "title": pt, "priority": p.get("priority")})
    priorities = {str(c.get("priority") or "P1") for c in cases}
    gaps = []
    if uncovered:
        gaps.append({"type": "uncovered_points", "items": uncovered[:8]})
    if cases and "P0" not in priorities and any(str(p.get("priority")) == "P0" for p in points):
        gaps.append({"type": "missing_p0", "items": [p for p in points if str(p.get("priority")) == "P0"][:5]})
    executable = sum(1 for c in cases if c.get("method") and (c.get("path") or c.get("url")))
    return {
        "point_count": len(points),
        "case_count": len(cases),
        "uncovered_count": len(uncovered),
        "executable_count": executable,
        "gaps": gaps,
        "ok": not gaps,
    }


def skill_compliance(req: EngineRequest, artifacts: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    skills = req.artifacts.get("skills") or []
    if not skills:
        return {"skills": [], "score": 1.0, "followed": [], "missed": []}
    blob = json.dumps(artifacts, ensure_ascii=False).lower()
    followed = []
    missed = []
    details = []
    for s in skills:
        name = str(s.get("name") or "skill")
        content = str(s.get("content") or "")
        keywords = _skill_keywords(content)
        hits = [k for k in keywords if k.lower() in blob]
        ratio = (len(hits) / len(keywords)) if keywords else 0.5
        ok = ratio >= 0.34 if keywords else True
        item = {"id": s.get("id"), "name": name, "ok": ok, "hits": hits[:8], "keywords": keywords[:8]}
        details.append(item)
        (followed if ok else missed).append(name)
    score = round(sum(1 for d in details if d["ok"]) / max(1, len(details)), 3)
    return {"kind": kind, "skills": details, "score": score, "followed": followed, "missed": missed}


def _skill_keywords(content: str) -> list[str]:
    lines = [ln.strip(" -*\t") for ln in content.splitlines() if ln.strip()]
    keys: list[str] = []
    for ln in lines[:12]:
        for part in re.split(r"[，,；;。/\s]+", ln):
            part = part.strip()
            if 2 <= len(part) <= 24 and part.lower() not in {"the", "and", "for", "with"}:
                keys.append(part)
    # de-dupe preserve order
    seen = set()
    out = []
    for k in keys:
        low = k.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(k)
    return out[:12]


async def repair_cases(req: EngineRequest, cases: list[dict[str, Any]], issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not settings.llm_enabled or not issues:
        # best-effort local fill
        required = required_fields(req)
        fixed = []
        for c in cases:
            row = {**c}
            for k in row.get("_schema_missing") or []:
                if k == "steps" and not row.get("steps"):
                    row["steps"] = ["准备请求", "发送接口", "校验响应"]
                elif k == "expected" and not row.get("expected"):
                    row["expected"] = "返回成功状态"
                elif k == "priority" and not row.get("priority"):
                    row["priority"] = "P1"
                elif k == "title" and not row.get("title"):
                    row["title"] = "未命名用例"
                elif k == "precondition" and not row.get("precondition"):
                    row["precondition"] = "服务可用"
            row.pop("_schema_missing", None)
            missing = [k for k in required if not _has(row, k)]
            if missing:
                row["_schema_missing"] = missing
            fixed.append(row)
        return fixed

    system = """你是用例修复助手。根据 schema 缺失项补全字段，不要删已有用例。
只输出 JSON：{"message":"...","test_cases":[...完整用例列表...]}"""
    payload = {
        "template": req.template.model_dump(by_alias=True) if req.template else {},
        "issues": issues,
        "test_cases": cases,
    }
    data = await complete_json(system, json.dumps(payload, ensure_ascii=False), model=req.model)
    repaired = data.get("test_cases") or cases
    return validate_cases(req, repaired)


async def fill_gaps(req: EngineRequest, cases: list[dict[str, Any]], critique: dict[str, Any]) -> list[dict[str, Any]]:
    gaps = critique.get("gaps") or []
    if not gaps:
        return cases
    uncovered = []
    for g in gaps:
        if g.get("type") == "uncovered_points":
            uncovered.extend(g.get("items") or [])
    if not uncovered:
        return cases

    if not settings.llm_enabled:
        extras = []
        for i, p in enumerate(uncovered[:3]):
            extras.append(
                {
                    "title": f"补齐-{p.get('title')}",
                    "precondition": "服务可用",
                    "steps": ["根据测试点构造请求", "发送接口", "校验响应"],
                    "expected": "符合测试点描述",
                    "priority": p.get("priority") or "P1",
                    "tags": ["缺口补齐"],
                    "method": "GET",
                    "path": "/api/example",
                    "assert": {"status_code": 200},
                    "extract": [],
                    "_from_point": p.get("title"),
                }
            )
        return validate_cases(req, cases + extras)

    system = """你是覆盖率补齐助手。仅为未覆盖的测试点补充用例，保留已有用例不变。
只输出 JSON：{"message":"...","test_cases":[...仅新增用例...]}"""
    payload = {
        "uncovered_points": uncovered[:8],
        "existing_titles": [c.get("title") for c in cases],
        "template": req.template.model_dump(by_alias=True) if req.template else {},
        "context_chunks": [c.model_dump() for c in req.context_chunks[:8]],
    }
    data = await complete_json(system, json.dumps(payload, ensure_ascii=False), model=req.model)
    extras = data.get("test_cases") or []
    return validate_cases(req, cases + extras)


def _has(case: dict[str, Any], key: str) -> bool:
    v = case.get(key)
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, list):
        return len(v) > 0
    if isinstance(v, dict):
        return len(v) > 0
    return True
