from __future__ import annotations

import asyncio
import io
import logging
import time
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.api.deps import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"], dependencies=[Depends(require_api_key)])

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/bmp", "application/octet-stream"}
MAX_BYTES = 12 * 1024 * 1024
# Inference cost grows with pixels; 1024 is enough for UI preview / pets.
DEFAULT_MAX_SIDE = 1024

_sessions: dict[str, object] = {}
_session_lock = asyncio.Lock()


def _get_session_sync(model: str):
    try:
        from rembg import new_session
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail="rembg not installed. Run: pip install \"rembg[cpu]\" pillow",
        ) from e
    if model not in _sessions:
        t0 = time.perf_counter()
        try:
            _sessions[model] = new_session(model)
        except Exception as e:
            logger.exception("rembg session failed model=%s", model)
            raise HTTPException(status_code=400, detail=f"invalid rembg model: {model} ({e})") from e
        logger.info("rembg session ready model=%s in %.1fs", model, time.perf_counter() - t0)
    return _sessions[model]


def _downscale(img, max_side: int):
    w, h = img.size
    m = max(w, h)
    if m <= max_side:
        return img
    scale = max_side / m
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    from PIL import Image

    return img.resize((nw, nh), Image.Resampling.LANCZOS)


def _run_rembg(raw: bytes, model: str, alpha_matting: bool, max_side: int) -> bytes:
    from rembg import remove
    from PIL import Image

    session = _get_session_sync(model)
    img = Image.open(io.BytesIO(raw))
    img = _downscale(img.convert("RGB"), max_side)
    t0 = time.perf_counter()
    out = remove(img, session=session, alpha_matting=alpha_matting)
    logger.info(
        "rembg infer model=%s size=%sx%s alpha=%s in %.1fs",
        model,
        img.size[0],
        img.size[1],
        alpha_matting,
        time.perf_counter() - t0,
    )
    if hasattr(out, "save"):
        buf = io.BytesIO()
        out.save(buf, format="PNG")
        return buf.getvalue()
    return out if isinstance(out, (bytes, bytearray)) else bytes(out)


@router.get("/rembg/models")
def list_rembg_models():
    return {
        "models": [
            {"id": "u2netp", "label": "u2netp（推荐·最快）", "fast": True},
            {"id": "u2net_human_seg", "label": "u2net_human_seg（人像）", "fast": True},
            {"id": "u2net", "label": "u2net（通用）", "fast": False},
            {"id": "isnet-general-use", "label": "isnet-general-use", "fast": False},
            {
                "id": "isnet-anime",
                "label": "isnet-anime（二次元·首次需下约176MB）",
                "fast": False,
            },
        ],
        "default": "u2netp",
        "note": "大图会自动缩到最长边 1024。发丝精修很慢，一般不必开。isnet-anime 首次下载很慢。",
    }


@router.post("/rembg")
async def remove_background(
    file: UploadFile = File(...),
    model: Literal["u2netp", "u2net", "u2net_human_seg", "isnet-anime", "isnet-general-use"] = Form("u2netp"),
    alpha_matting: bool = Form(False),
    max_side: int = Form(DEFAULT_MAX_SIDE),
):
    """Remove image background via rembg public API; returns PNG with alpha."""
    ctype = (file.content_type or "application/octet-stream").lower()
    if ctype not in ALLOWED_TYPES and not ctype.startswith("image/"):
        raise HTTPException(status_code=400, detail=f"unsupported content type: {ctype}")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty file")
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="file too large (max 12MB)")

    side = max(256, min(int(max_side or DEFAULT_MAX_SIDE), 2048))
    try:
        out = await asyncio.to_thread(_run_rembg, raw, model, alpha_matting, side)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("rembg remove failed")
        raise HTTPException(status_code=500, detail=f"rembg failed: {e}") from e

    return Response(
        content=out,
        media_type="image/png",
        headers={"Content-Disposition": 'attachment; filename="rembg-output.png"'},
    )
