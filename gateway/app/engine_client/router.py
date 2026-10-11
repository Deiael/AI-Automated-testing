from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ai_test_contracts import EngineEvent, EngineRequest
from app.config import settings
from app.persistence.models import EngineProfile, Project

logger = logging.getLogger(__name__)


class EngineRouter:
    def resolve(
        self,
        db: Session,
        project_id: str,
        override_profile_id: str | None = None,
    ) -> EngineProfile:
        profile_id = override_profile_id
        if not profile_id:
            project = db.get(Project, project_id)
            profile_id = project.engine_profile_id if project else None
        if profile_id:
            profile = db.get(EngineProfile, profile_id)
            if profile:
                return profile
        # ensure default
        default = db.query(EngineProfile).filter(EngineProfile.name == "default").first()
        if default:
            return default
        default = EngineProfile(
            name="default",
            engine_base_url=settings.engine_default_url,
            model="gpt-4o-mini",
            vendor="langgraph",
        )
        db.add(default)
        db.commit()
        db.refresh(default)
        return default

    async def health(self, profile: EngineProfile) -> dict[str, Any]:
        url = profile.engine_base_url.rstrip("/") + "/health"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                return {"ok": True, "profile_id": profile.id, "detail": data}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "profile_id": profile.id, "error": str(exc)}

    async def stream(self, profile: EngineProfile, req: EngineRequest) -> AsyncIterator[EngineEvent]:
        url = profile.engine_base_url.rstrip("/") + "/v1/stream"
        payload = req.model_dump(mode="json")
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    if resp.status_code >= 400:
                        body = await resp.aread()
                        yield EngineEvent(
                            event="error",
                            data={
                                "code": "ENGINE_UNAVAILABLE",
                                "message": body.decode("utf-8", errors="ignore"),
                            },
                        )
                        yield EngineEvent(event="done", data={"finish_reason": "error"})
                        return
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if not raw:
                            continue
                        try:
                            obj = json.loads(raw)
                            yield EngineEvent(event=obj.get("event"), data=obj.get("data") or {})
                        except Exception:  # noqa: BLE001
                            logger.warning("bad engine sse line: %s", raw)
        except httpx.RequestError as exc:
            yield EngineEvent(
                event="error",
                data={"code": "ENGINE_UNAVAILABLE", "message": str(exc)},
            )
            yield EngineEvent(event="done", data={"finish_reason": "error"})


engine_router = EngineRouter()
