from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.stream import router as stream_router
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="AI-Test Engine", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(stream_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "layer": "engine",
        "llm_enabled": settings.llm_enabled,
        "model": settings.openai_model,
        "base_url": settings.openai_base_url,
        "fallback_mock": settings.llm_fallback_mock,
    }
