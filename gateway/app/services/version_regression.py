from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.persistence.models import (
    ApiSpec,
    Project,
    TestCase,
    TestPoint,
    TestReport,
    TestRun,
    VersionBaseline,
)
from app.services.coverage import _case_operation_key, coverage_board
from app.services.openapi_import import build_point_and_cases, operation_key


def capture_current(
    db: Session,
    *,
    project_id: str,
    pipeline_id: str | None,
) -> dict[str, Any]:
    project = db.get(Project, project_id)
    spec = _latest_spec(db, project_id, pipeline_id)
    ops = list((spec.operations_json or []) if spec else [])
    cases = _case_summaries(db, project_id, pipeline_id)
    report = _latest_report(db, project_id, pipeline_id)
    cov = coverage_board(db, project_id=project_id, pipeline_id=pipeline_id)
    return {
        "spec_id": spec.id if spec else None,
        "spec_title": (spec.title if spec else "") or "",
        "spec_version": (spec.version if spec else "") or "",
        "operations": ops,
        "cases": cases,
        "report": report,
        "coverage": {
            "api_ratio": (cov.get("api") or {}).get("ratio"),
            "req_ratio": (cov.get("requirement") or {}).get("ratio"),
            "overall_ratio": cov.get("overall_ratio"),
        },
        "runtime_base_url": (project.runtime_base_url if project else "") or "",
    }


def save_baseline(
    db: Session,
    *,
    project_id: str,
    pipeline_id: str | None,
    name: str,
    note: str = "",
) -> VersionBaseline:
    snap = capture_current(db, project_id=project_id, pipeline_id=pipeline_id)
    row = VersionBaseline(
        project_id=project_id,
        pipeline_id=pipeline_id,
        name=(name or "v1").strip(),
        note=note or "",
        spec_id=snap.get("spec_id"),
        spec_title=snap.get("spec_title") or "",
        operations_json=snap.get("operations") or [],
        cases_json=snap.get("cases") or [],
        report_json=snap.get("report") or {},
        runtime_base_url=snap.get("runtime_base_url") or "",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def build_plan(
    db: Session,
    *,
    project_id: str,
    pipeline_id: str | None,
    baseline_id: str,
) -> dict[str, Any]:
    old = db.get(VersionBaseline, baseline_id)
    if not old or old.project_id != project_id:
        raise ValueError("baseline not found")
    current = capture_current(db, project_id=project_id, pipeline_id=pipeline_id)
    diff = diff_operations(old.operations_json or [], current.get("operations") or [])
    predict = predict_from_baseline(old)
    localize = localize_from_diff(diff)
    return {
        "baseline": _baseline_out(old),
        "current": {
            "spec_title": current.get("spec_title"),
            "spec_version": current.get("spec_version"),
            "operations": len(current.get("operations") or []),
            "cases": len(current.get("cases") or []),
            "coverage": current.get("coverage"),
            "runtime_base_url": current.get("runtime_base_url"),
        },
        "diff": {
            "added": len(diff["added"]),
            "removed": len(diff["removed"]),
            "changed": len(diff["changed"]),
            "unchanged": len(diff["unchanged"]),
            "added_ops": diff["added"],
            "removed_ops": diff["removed"],
            "changed_ops": diff["changed"],
        },
        "predict": predict,  # 旧版本主线：基线预测
        "localize": localize,  # 新版本主线：差异定位
        "seed_ops": _merge_seed_ops(predict, localize, current.get("operations") or []),
    }


def generate_from_plan(
    db: Session,
    *,
    project_id: str,
    pipeline_id: str | None,
    plan: dict[str, Any],
    confirm: bool = True,
) -> dict[str, Any]:
    existing_titles = {
        r.title
        for r in db.query(TestCase).filter(TestCase.project_id == project_id, TestCase.pipeline_id == pipeline_id).all()
    }
    points_n = 0
    cases_n = 0
    case_ids: list[str] = []
    status = "CONFIRMED" if confirm else "DRAFT"

    for seed in plan.get("seed_ops") or []:
        op = seed.get("op") or {}
        track = seed.get("track") or "localize"
        reason = seed.get("reason") or ""
        if not op.get("method") or not op.get("path"):
            continue
        point_data, cases_data = build_point_and_cases(
            op, project_id=project_id, pipeline_id=pipeline_id, confirm=confirm
        )
        point_data["content_json"] = {
            **(point_data.get("content_json") or {}),
            "suite": "regression",
            "track": track,
            "reason": reason,
        }
        prefix = "[定位]" if track == "localize" else "[预测]"
        point_data["title"] = f"{prefix} {point_data['title']}"
        point = TestPoint(**point_data)
        db.add(point)
        db.flush()
        points_n += 1
        for cd in cases_data:
            title = f"{prefix} {cd['title']}"
            if title in existing_titles:
                continue
            content = dict(cd.get("content_json") or {})
            content.update(
                {
                    "suite": "regression",
                    "track": track,
                    "reason": reason,
                    "tags": list(content.get("tags") or []) + ["回归", track],
                }
            )
            row = TestCase(
                project_id=project_id,
                pipeline_id=pipeline_id,
                test_point_id=point.id,
                title=title,
                content_json=content,
                status=status,
                confidence=0.8 if track == "localize" else 0.72,
            )
            db.add(row)
            db.flush()
            case_ids.append(row.id)
            existing_titles.add(title)
            cases_n += 1

    db.commit()
    return {"points_created": points_n, "cases_created": cases_n, "case_ids": case_ids}


def diff_operations(old_ops: list[dict[str, Any]], new_ops: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    old_map = {_op_key(o): o for o in old_ops if isinstance(o, dict)}
    new_map = {_op_key(o): o for o in new_ops if isinstance(o, dict)}
    added, removed, changed, unchanged = [], [], [], []
    for key, nop in new_map.items():
        if key not in old_map:
            added.append(nop)
        elif _op_fingerprint(old_map[key]) != _op_fingerprint(nop):
            changed.append({**nop, "before": {"summary": old_map[key].get("summary"), "status_codes": old_map[key].get("status_codes")}})
        else:
            unchanged.append(nop)
    for key, oop in old_map.items():
        if key not in new_map:
            removed.append(oop)
    return {"added": added, "removed": removed, "changed": changed, "unchanged": unchanged}


def predict_from_baseline(old: VersionBaseline) -> list[dict[str, Any]]:
    """Old-version track: use baseline failures / thin coverage to predict risk."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    report = old.report_json or {}
    details = ((report.get("detail") or {}).get("details") if isinstance(report.get("detail"), dict) else None) or []
    if not details and isinstance(report.get("failed_details"), list):
        details = report["failed_details"]
    for item in details:
        if not isinstance(item, dict) or item.get("ok"):
            continue
        key = str(item.get("operation_key") or "")
        if not key:
            method = item.get("method")
            path = item.get("path") or item.get("url")
            if method and path:
                key = operation_key(str(method), str(path))
        if not key or key in seen:
            continue
        seen.add(key)
        op = _find_op(old.operations_json or [], key) or _op_from_case_like(item)
        out.append(
            {
                "track": "predict",
                "reason": f"旧版失败：{item.get('case_title') or item.get('error') or key}",
                "key": key,
                "op": op,
            }
        )

    case_keys = {str(c.get("operation_key") or "") for c in (old.cases_json or []) if isinstance(c, dict)}
    for op in old.operations_json or []:
        if not isinstance(op, dict):
            continue
        key = _op_key(op)
        if key in seen or (key in case_keys and key):
            continue
        if key in case_keys:
            continue
        # uncovered in old baseline
        if not any(str(c.get("operation_key") or "") == key for c in (old.cases_json or []) if isinstance(c, dict)):
            seen.add(key)
            out.append({"track": "predict", "reason": "旧版无对应用例，回归时易漏", "key": key, "op": op})
    return out[:40]


def localize_from_diff(diff: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """New-version track: localize problems on added/changed APIs."""
    out = []
    for op in diff.get("added") or []:
        out.append({"track": "localize", "reason": "新版本新增接口", "key": _op_key(op), "op": op})
    for op in diff.get("changed") or []:
        out.append({"track": "localize", "reason": "新版本接口契约变化", "key": _op_key(op), "op": op})
    for op in diff.get("removed") or []:
        out.append(
            {
                "track": "localize",
                "reason": "新版本删除接口，需确认调用方/兼容",
                "key": _op_key(op),
                "op": op,
                "skip_http": True,
            }
        )
    return out


def _merge_seed_ops(
    predict: list[dict[str, Any]],
    localize: list[dict[str, Any]],
    current_ops: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    current_map = {_op_key(o): o for o in current_ops if isinstance(o, dict)}
    seeds: list[dict[str, Any]] = []
    seen: set[str] = set()
    # localization first (new version)
    for item in localize:
        if item.get("skip_http"):
            continue
        key = item.get("key") or ""
        op = current_map.get(key) or item.get("op")
        if not op or key in seen:
            continue
        seen.add(key)
        seeds.append({**item, "op": op})
    for item in predict:
        key = item.get("key") or ""
        op = current_map.get(key) or item.get("op")
        if not op or key in seen:
            continue
        # only generate HTTP if the op still exists in new version
        if key not in current_map:
            continue
        seen.add(key)
        seeds.append({**item, "op": op})
    return seeds


def _latest_spec(db: Session, project_id: str, pipeline_id: str | None) -> ApiSpec | None:
    q = db.query(ApiSpec).filter(ApiSpec.project_id == project_id)
    if pipeline_id:
        q = q.filter((ApiSpec.pipeline_id == pipeline_id) | (ApiSpec.pipeline_id.is_(None)))
    return q.order_by(ApiSpec.created_at.desc()).first()


def _case_summaries(db: Session, project_id: str, pipeline_id: str | None) -> list[dict[str, Any]]:
    q = db.query(TestCase).filter(TestCase.project_id == project_id)
    if pipeline_id:
        q = q.filter(TestCase.pipeline_id == pipeline_id)
    rows = q.order_by(TestCase.created_at.desc()).limit(500).all()
    out = []
    for r in rows:
        c = r.content_json or {}
        out.append(
            {
                "id": r.id,
                "title": r.title,
                "status": r.status,
                "method": c.get("method"),
                "path": c.get("path"),
                "operation_key": _case_operation_key(r),
            }
        )
    return out


def _latest_report(db: Session, project_id: str, pipeline_id: str | None) -> dict[str, Any]:
    q = db.query(TestRun).filter(TestRun.project_id == project_id)
    if pipeline_id:
        q = q.filter(TestRun.pipeline_id == pipeline_id)
    run = q.order_by(TestRun.created_at.desc()).first()
    if not run:
        return {}
    rep = db.query(TestReport).filter(TestReport.run_id == run.id).order_by(TestReport.created_at.desc()).first()
    if not rep:
        return {"run_id": run.id, "run_status": run.status}
    details = (rep.detail_json or {}).get("details") or []
    failed = [d for d in details if isinstance(d, dict) and not d.get("ok")]
    return {
        "run_id": run.id,
        "report_id": rep.id,
        "summary": rep.summary_json or {},
        "failed_details": failed[:50],
        "detail": {"details": failed[:50]},
    }


def _op_key(op: dict[str, Any]) -> str:
    return operation_key(str(op.get("method") or "GET"), str(op.get("path") or "/"))


def _op_fingerprint(op: dict[str, Any]) -> tuple:
    codes = tuple(sorted(str(x) for x in (op.get("status_codes") or [])))
    return (
        _op_key(op),
        str(op.get("summary") or ""),
        codes,
        bool(op.get("has_request_body")),
        bool(op.get("security")),
    )


def _find_op(ops: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    for o in ops:
        if isinstance(o, dict) and _op_key(o) == key:
            return o
    return None


def _op_from_case_like(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "method": str(item.get("method") or "GET").upper(),
        "path": str(item.get("path") or "/"),
        "summary": item.get("case_title") or item.get("title") or "",
        "operation_id": item.get("operation_id") or "",
        "status_codes": [],
        "security": None,
        "sample_body": None,
    }


def _baseline_out(row: VersionBaseline) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "note": row.note,
        "spec_title": row.spec_title,
        "operations": len(row.operations_json or []),
        "cases": len(row.cases_json or []),
        "runtime_base_url": row.runtime_base_url,
        "created_at": row.created_at,
        "has_failures": bool((row.report_json or {}).get("failed_details") or (row.report_json or {}).get("summary", {}).get("failed")),
    }
