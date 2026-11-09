from __future__ import annotations

from typing import Any
from urllib.parse import urljoin, urlparse

from app.persistence.models import Project, TestCase


def case_payload(row: TestCase) -> dict[str, Any]:
    content = dict(row.content_json or {})
    content.pop("_confidence", None)
    return {
        **content,
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "confidence": float(row.confidence or 0),
        "project_id": row.project_id,
        "pipeline_id": row.pipeline_id,
    }


def engine_artifact(row: TestCase) -> dict[str, Any]:
    content = dict(row.content_json or {})
    content.pop("_confidence", None)
    return {
        **content,
        "id": row.id,
        "title": row.title,
        "confidence": float(row.confidence or 0),
        "status": row.status,
    }


def export_json(rows: list[TestCase]) -> dict[str, Any]:
    return {"format": "ai-test-cases-v1", "count": len(rows), "cases": [case_payload(r) for r in rows]}


def export_postman(rows: list[TestCase], project: Project | None = None) -> dict[str, Any]:
    base = (project.runtime_base_url if project else "") or ""
    items = []
    for row in rows:
        c = case_payload(row)
        method = str(c.get("method") or "GET").upper()
        path = str(c.get("path") or "/")
        url = str(c.get("url") or "").strip()
        if not url:
            url = urljoin(base.rstrip("/") + "/", path.lstrip("/")) if base else path
        parsed = urlparse(url)
        headers = c.get("headers") or {}
        if not isinstance(headers, dict):
            headers = {}
        body = c.get("body")
        item: dict[str, Any] = {
            "name": row.title,
            "request": {
                "method": method,
                "header": [{"key": str(k), "value": str(v)} for k, v in headers.items()],
                "url": url if parsed.scheme else path,
            },
        }
        if body not in (None, "", {}):
            item["request"]["body"] = {
                "mode": "raw",
                "raw": body if isinstance(body, str) else __import__("json").dumps(body, ensure_ascii=False),
                "options": {"raw": {"language": "json"}},
            }
        desc_parts = [str(c.get("precondition") or ""), str(c.get("expected") or "")]
        if any(desc_parts):
            item["request"]["description"] = "\n".join(p for p in desc_parts if p)
        items.append(item)
    name = (project.name + " · cases") if project else "AI-Test cases"
    return {
        "info": {
            "name": name,
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "description": "Exported from AI-Test",
        },
        "item": items,
        "variable": [{"key": k, "value": str(v)} for k, v in ((project.runtime_variables if project else {}) or {}).items()],
    }
