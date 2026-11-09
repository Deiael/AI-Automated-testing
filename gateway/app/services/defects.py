from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.persistence.models import DefectIssue, Project, TestRun

logger = logging.getLogger(__name__)


def sync_failures_to_issues(
    db: Session,
    *,
    project_id: str,
    pipeline_id: str | None,
    run_row: TestRun,
    failed_details: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    project = db.get(Project, project_id)
    if not project:
        return []
    cfg = dict(project.defect_config or {})
    if not cfg.get("enabled"):
        return []
    provider = str(cfg.get("provider") or "github").lower()
    created: list[dict[str, Any]] = []
    for item in failed_details:
        case_id = item.get("case_id")
        title = str(item.get("case_title") or case_id or "failed case")
        # de-dupe open issues for same case
        if case_id:
            exists = (
                db.query(DefectIssue)
                .filter(
                    DefectIssue.project_id == project_id,
                    DefectIssue.case_id == str(case_id),
                    DefectIssue.status == "open",
                )
                .first()
            )
            if exists:
                created.append(
                    {
                        "skipped": True,
                        "reason": "already_open",
                        "issue_id": exists.id,
                        "external_url": exists.external_url,
                        "case_id": case_id,
                    }
                )
                continue
        issue_title = f"[AI-Test] {title} failed"
        body = _issue_body(item, run_id=run_row.id, pipeline_id=pipeline_id)
        try:
            if provider == "github":
                ext = _create_github_issue(cfg, title=issue_title, body=body)
            elif provider == "webhook":
                ext = _post_webhook(cfg, title=issue_title, body=body, item=item, run_id=run_row.id)
            else:
                logger.warning("unsupported defect provider: %s", provider)
                continue
        except Exception as exc:  # noqa: BLE001
            logger.exception("create defect failed")
            created.append({"ok": False, "error": str(exc), "case_id": case_id})
            continue

        row = DefectIssue(
            project_id=project_id,
            pipeline_id=pipeline_id,
            run_id=run_row.id,
            case_id=str(case_id) if case_id else None,
            case_title=title,
            provider=provider,
            external_id=str(ext.get("id") or ""),
            external_url=str(ext.get("url") or ""),
            title=issue_title,
            status="open",
            payload_json={"detail": item, "external": ext},
        )
        db.add(row)
        db.flush()
        created.append(
            {
                "ok": True,
                "issue_id": row.id,
                "external_id": row.external_id,
                "external_url": row.external_url,
                "case_id": case_id,
            }
        )
    if created:
        db.commit()
    return created


def list_defects(
    db: Session,
    *,
    project_id: str,
    pipeline_id: str | None = None,
) -> list[DefectIssue]:
    q = db.query(DefectIssue).filter(DefectIssue.project_id == project_id)
    if pipeline_id:
        q = q.filter(DefectIssue.pipeline_id == pipeline_id)
    return q.order_by(DefectIssue.created_at.desc()).all()


def _issue_body(item: dict[str, Any], *, run_id: str, pipeline_id: str | None) -> str:
    lines = [
        "## Failed case",
        f"- **Title**: {item.get('case_title')}",
        f"- **Case ID**: {item.get('case_id')}",
        f"- **Run ID**: {run_id}",
        f"- **Pipeline**: {pipeline_id or '-'}",
        f"- **Status code**: {item.get('status_code')}",
        f"- **OK**: {item.get('ok')}",
        "",
        "### Error / response",
        "```",
        str(item.get("error") or item.get("message") or item.get("response") or item)[:4000],
        "```",
        "",
        "_Auto-created by AI-Test defect linkage._",
    ]
    return "\n".join(lines)


def _create_github_issue(cfg: dict[str, Any], *, title: str, body: str) -> dict[str, Any]:
    token = str(cfg.get("token") or "").strip()
    repo = str(cfg.get("repo") or "").strip()  # owner/name
    if not token or not repo:
        raise ValueError("defect_config.token and defect_config.repo required for github")
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    labels = cfg.get("labels") if isinstance(cfg.get("labels"), list) else ["ai-test", "auto"]
    payload = {"title": title, "body": body, "labels": labels}
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    return {"id": data.get("number"), "url": data.get("html_url"), "raw": {"number": data.get("number")}}


def _post_webhook(
    cfg: dict[str, Any],
    *,
    title: str,
    body: str,
    item: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    url = str(cfg.get("webhook_url") or "").strip()
    if not url:
        raise ValueError("defect_config.webhook_url required for webhook provider")
    payload = {"title": title, "body": body, "item": item, "run_id": run_id}
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        try:
            data = resp.json()
        except Exception:  # noqa: BLE001
            data = {"status_code": resp.status_code, "text": resp.text[:500]}
    return {"id": str(data.get("id") or resp.status_code), "url": str(data.get("url") or url), "raw": data}
