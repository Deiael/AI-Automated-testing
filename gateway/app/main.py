from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import artifacts, engines, mcp_servers, pipelines, projects, rag, sessions, skills
from app.bootstrap import seed_default_engine
from app.config import settings
from app.persistence.db import SessionLocal, init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="AI-Test Gateway", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(pipelines.router)
app.include_router(engines.router)
app.include_router(rag.router)
app.include_router(skills.router)
app.include_router(mcp_servers.router)
app.include_router(sessions.router)
app.include_router(artifacts.router)


@app.on_event("startup")
def on_startup() -> None:
    settings.ensure_dirs()
    init_db()
    db = SessionLocal()
    try:
        seed_default_engine(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "layer": "gateway"}


@app.get("/api/health")
def api_health():
    return {"status": "ok", "layer": "gateway"}
