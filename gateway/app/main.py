from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    analytics,
    artifacts,
    auth,
    ci,
    coverage,
    engines,
    mcp_servers,
    openapi_specs,
    pipelines,
    projects,
    rag,
    regression,
    sessions,
    skills,
    tools,
)
from app.bootstrap import seed_default_engine
from app.config import settings
from app.persistence.db import SessionLocal, init_db
from app.services.auth import seed_admin
from app.services.scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="AI-Test Gateway", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(pipelines.router)
app.include_router(engines.router)
app.include_router(rag.router)
app.include_router(skills.router)
app.include_router(mcp_servers.router)
app.include_router(sessions.router)
app.include_router(artifacts.router)
app.include_router(tools.router)
app.include_router(analytics.router)
app.include_router(openapi_specs.router)
app.include_router(coverage.router)
app.include_router(ci.router)
app.include_router(regression.router)


@app.on_event("startup")
def on_startup() -> None:
    settings.ensure_dirs()
    init_db()
    db = SessionLocal()
    try:
        seed_default_engine(db)
        seed_admin(db)
    finally:
        db.close()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    shutdown_scheduler()


@app.get("/health")
def health():
    return {"status": "ok", "layer": "gateway"}


@app.get("/api/health")
def api_health():
    return {"status": "ok", "layer": "gateway"}
