from __future__ import annotations

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ai_test_contracts import EngineEvent, EngineRequest
from app.graphs import stream_for

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/v1/stream")
async def stream(req: EngineRequest):
    async def event_gen():
        try:
            async for ev in stream_for(req):
                yield _sse(ev)
        except Exception as exc:  # noqa: BLE001
            logger.exception("engine stream error")
            err = EngineEvent(event="error", data={"code": "ENGINE_STREAM_ERROR", "message": str(exc)})
            yield _sse(err)
            yield _sse(EngineEvent(event="done", data={"finish_reason": "error"}))

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(ev: EngineEvent) -> str:
    payload = {"event": ev.event, "data": ev.data}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
