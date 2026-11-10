from __future__ import annotations

import uuid
from typing import Any

from app.persistence.models import Project


def list_envs(project: Project) -> list[dict[str, Any]]:
    envs = [e for e in (project.runtime_envs or []) if isinstance(e, dict)]
    if envs:
        return envs
    # back-compat: lift legacy single Base URL into a default env
    base = (project.runtime_base_url or "").strip()
    return [
        {
            "id": "default",
            "name": "default",
            "base_url": base,
            "headers": project.runtime_headers or {},
            "variables": project.runtime_variables or {},
            "timeout_sec": 30,
            "is_default": True,
        }
    ]


def resolve_env(project: Project, env_id: str | None = None) -> dict[str, Any]:
    envs = list_envs(project)
    if env_id:
        for e in envs:
            if str(e.get("id")) == str(env_id) or str(e.get("name")) == str(env_id):
                return _normalize(e, project)
    for e in envs:
        if e.get("is_default"):
            return _normalize(e, project)
    return _normalize(envs[0], project)


def upsert_default_from_legacy(envs: list[dict[str, Any]], project: Project) -> list[dict[str, Any]]:
    """Keep runtime_base_url in sync with the default env."""
    if not envs:
        return list_envs(project)
    out = []
    seen_default = False
    for e in envs:
        row = dict(e)
        if not row.get("id"):
            row["id"] = str(uuid.uuid4())
        if row.get("is_default"):
            if seen_default:
                row["is_default"] = False
            seen_default = True
        out.append(row)
    if not seen_default and out:
        out[0]["is_default"] = True
    return out


def apply_default_to_project(project: Project, envs: list[dict[str, Any]]) -> None:
    default = next((e for e in envs if e.get("is_default")), envs[0] if envs else None)
    if not default:
        return
    project.runtime_base_url = str(default.get("base_url") or "")
    project.runtime_headers = default.get("headers") or {}
    project.runtime_variables = default.get("variables") or {}


def _normalize(env: dict[str, Any], project: Project) -> dict[str, Any]:
    headers = dict(project.runtime_headers or {})
    headers.update(env.get("headers") or {})
    variables = dict(project.runtime_variables or {})
    variables.update(env.get("variables") or {})
    base = str(env.get("base_url") or project.runtime_base_url or "")
    timeout = int(env.get("timeout_sec") or 30)
    return {
        "id": str(env.get("id") or "default"),
        "name": str(env.get("name") or "default"),
        "base_url": base,
        "headers": {str(k): str(v) for k, v in headers.items() if v is not None},
        "variables": variables,
        "timeout_sec": max(5, min(timeout, 180)),
        "is_default": bool(env.get("is_default")),
    }
