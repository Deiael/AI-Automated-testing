from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.persistence import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _sqlite_add_missing_columns()


def _sqlite_add_missing_columns() -> None:
    """Best-effort ALTER for existing SQLite DBs (create_all won't add columns)."""
    if not settings.database_url.startswith("sqlite"):
        return
    alters = [
        ("rag_documents", "kb_id", "VARCHAR(36)"),
        ("rag_documents", "chunk_strategy", "VARCHAR(32) DEFAULT ''"),
        ("rag_documents", "chunks_json", "JSON"),
    ]
    with engine.begin() as conn:
        for table, col, decl in alters:
            rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            names = {r[1] for r in rows}
            if col not in names:
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
