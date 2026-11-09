from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.persistence.models import ApiSpec, RagDocument, TestCase, TestPoint
from app.services.openapi_import import normalize_path, operation_key


def api_coverage(
    db: Session,
    *,
    project_id: str,
    pipeline_id: str | None = None,
    spec_id: str | None = None,
) -> dict[str, Any]:
    ops = _collect_operations(db, project_id=project_id, pipeline_id=pipeline_id, spec_id=spec_id)
    cases = _cases(db, project_id, pipeline_id)
    covered_keys: set[str] = set()
    case_by_key: dict[str, list[dict[str, Any]]] = {}
    for c in cases:
        key = _case_operation_key(c)
        if not key:
            continue
        case_by_key.setdefault(key, []).append({"id": c.id, "title": c.title, "status": c.status})
        covered_keys.add(key)

    items = []
    covered = 0
    for op in ops:
        key = op["key"]
        matched = case_by_key.get(key) or []
        ok = bool(matched)
        if ok:
            covered += 1
        items.append({**op, "covered": ok, "cases": matched})

    total = len(ops)
    return {
        "kind": "api",
        "total": total,
        "covered": covered,
        "uncovered": max(0, total - covered),
        "ratio": round(covered / total, 4) if total else 0.0,
        "items": items,
    }


def requirement_coverage(
    db: Session,
    *,
    project_id: str,
    pipeline_id: str | None = None,
) -> dict[str, Any]:
    """Map RAG requirement docs + requirement-sourced test points to generated cases."""
    docs_q = db.query(RagDocument).filter(RagDocument.project_id == project_id)
    if pipeline_id:
        docs_q = docs_q.filter((RagDocument.pipeline_id == pipeline_id) | (RagDocument.pipeline_id.is_(None)))
    docs = docs_q.order_by(RagDocument.created_at.desc()).all()

    points_q = db.query(TestPoint).filter(TestPoint.project_id == project_id)
    if pipeline_id:
        points_q = points_q.filter(TestPoint.pipeline_id == pipeline_id)
    points = points_q.all()

    cases = _cases(db, project_id, pipeline_id)
    cases_by_point: dict[str, list[TestCase]] = {}
    for c in cases:
        if c.test_point_id:
            cases_by_point.setdefault(c.test_point_id, []).append(c)

    # Requirement units = docs + non-openapi points
    units: list[dict[str, Any]] = []
    for d in docs:
        units.append(
            {
                "id": d.id,
                "kind": "requirement_doc",
                "title": d.title,
                "source": d.source,
                "linked_points": [p.id for p in points if _point_mentions_doc(p, d)],
            }
        )
    for p in points:
        src = (p.content_json or {}).get("source")
        if src == "openapi":
            continue
        units.append(
            {
                "id": p.id,
                "kind": "test_point",
                "title": p.title,
                "source": src or "manual",
                "status": p.status,
                "case_count": len(cases_by_point.get(p.id) or []),
            }
        )

    items = []
    covered = 0
    for u in units:
        if u["kind"] == "requirement_doc":
            linked = u.get("linked_points") or []
            case_n = sum(len(cases_by_point.get(pid) or []) for pid in linked)
            # also fuzzy: any case title overlapping doc title tokens
            if case_n == 0:
                case_n = sum(1 for c in cases if _title_overlap(u["title"], c.title))
            ok = case_n > 0 or bool(linked)
        else:
            case_n = int(u.get("case_count") or 0)
            ok = case_n > 0
        if ok:
            covered += 1
        items.append({**u, "covered": ok, "case_count": case_n})

    total = len(items)
    return {
        "kind": "requirement",
        "total": total,
        "covered": covered,
        "uncovered": max(0, total - covered),
        "ratio": round(covered / total, 4) if total else 0.0,
        "items": items,
    }


def coverage_board(
    db: Session,
    *,
    project_id: str,
    pipeline_id: str | None = None,
    spec_id: str | None = None,
) -> dict[str, Any]:
    api = api_coverage(db, project_id=project_id, pipeline_id=pipeline_id, spec_id=spec_id)
    req = requirement_coverage(db, project_id=project_id, pipeline_id=pipeline_id)
    return {
        "project_id": project_id,
        "pipeline_id": pipeline_id,
        "api": api,
        "requirement": req,
        "overall_ratio": round(((api["ratio"] + req["ratio"]) / 2.0), 4)
        if (api["total"] or req["total"])
        else 0.0,
    }


def _collect_operations(
    db: Session,
    *,
    project_id: str,
    pipeline_id: str | None,
    spec_id: str | None,
) -> list[dict[str, Any]]:
    q = db.query(ApiSpec).filter(ApiSpec.project_id == project_id)
    if spec_id:
        q = q.filter(ApiSpec.id == spec_id)
    elif pipeline_id:
        q = q.filter((ApiSpec.pipeline_id == pipeline_id) | (ApiSpec.pipeline_id.is_(None)))
    specs = q.order_by(ApiSpec.created_at.desc()).all()
    seen: set[str] = set()
    ops: list[dict[str, Any]] = []
    for spec in specs:
        for op in spec.operations_json or []:
            if not isinstance(op, dict):
                continue
            key = operation_key(str(op.get("method") or "GET"), str(op.get("path") or "/"))
            if key in seen:
                continue
            seen.add(key)
            ops.append(
                {
                    "key": key,
                    "method": str(op.get("method") or "GET").upper(),
                    "path": str(op.get("path") or "/"),
                    "summary": op.get("summary") or key,
                    "spec_id": spec.id,
                    "spec_title": spec.title,
                }
            )
    # Fallback: openapi-sourced test points
    if not ops:
        pq = db.query(TestPoint).filter(TestPoint.project_id == project_id)
        if pipeline_id:
            pq = pq.filter(TestPoint.pipeline_id == pipeline_id)
        for p in pq.all():
            cj = p.content_json or {}
            if cj.get("source") != "openapi":
                continue
            key = cj.get("key") or operation_key(str(cj.get("method") or "GET"), str(cj.get("path") or "/"))
            if key in seen:
                continue
            seen.add(key)
            ops.append(
                {
                    "key": key,
                    "method": str(cj.get("method") or "GET").upper(),
                    "path": str(cj.get("path") or "/"),
                    "summary": p.title,
                    "spec_id": None,
                    "spec_title": "from test points",
                }
            )
    return ops


def _cases(db: Session, project_id: str, pipeline_id: str | None) -> list[TestCase]:
    q = db.query(TestCase).filter(TestCase.project_id == project_id)
    if pipeline_id:
        q = q.filter(TestCase.pipeline_id == pipeline_id)
    return q.all()


def _case_operation_key(case: TestCase) -> str | None:
    c = case.content_json or {}
    if c.get("operation_key"):
        return str(c["operation_key"])
    method = c.get("method")
    path = c.get("path") or c.get("url")
    if method and path:
        # strip query / host if url
        path_s = str(path)
        if "://" in path_s:
            try:
                from urllib.parse import urlparse

                path_s = urlparse(path_s).path or "/"
            except Exception:  # noqa: BLE001
                path_s = "/"
        return operation_key(str(method), path_s)
    return None


def _point_mentions_doc(point: TestPoint, doc: RagDocument) -> bool:
    blob = f"{point.title} {point.content_json}".lower()
    title = (doc.title or "").lower().strip()
    if title and title in blob:
        return True
    return False


def _title_overlap(a: str, b: str) -> bool:
    ta = {t for t in _tokens(a) if len(t) > 1}
    tb = {t for t in _tokens(b) if len(t) > 1}
    if not ta or not tb:
        return False
    return len(ta & tb) >= max(1, min(2, len(ta) // 2))


def _tokens(s: str) -> list[str]:
    import re

    return re.findall(r"[\w\u4e00-\u9fff]+", (s or "").lower())


# re-export for tests
__all__ = ["api_coverage", "requirement_coverage", "coverage_board", "normalize_path"]
