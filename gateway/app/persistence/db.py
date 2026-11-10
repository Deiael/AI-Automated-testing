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
    _add_missing_columns()


_COLUMN_ALTERS = [
    ("rag_documents", "kb_id", "VARCHAR(36)"),
    ("rag_documents", "pipeline_id", "VARCHAR(36)"),
    ("rag_documents", "chunk_strategy", "VARCHAR(32) DEFAULT ''"),
    ("rag_documents", "chunks_json", "JSON"),
    ("sessions", "pipeline_id", "VARCHAR(36)"),
    ("test_points", "pipeline_id", "VARCHAR(36)"),
    ("test_cases", "pipeline_id", "VARCHAR(36)"),
    ("test_runs", "pipeline_id", "VARCHAR(36)"),
    ("projects", "runtime_variables", "JSON"),
    ("projects", "defect_config", "JSON"),
    ("projects", "owner_user_id", "VARCHAR(36)"),
    ("projects", "runtime_envs", "JSON"),
    ("pipelines", "kind", "VARCHAR(32) DEFAULT 'api'"),
]


def _add_missing_columns() -> None:
    """Best-effort ALTER — create_all will not add columns to existing tables."""
    dialect = engine.dialect.name
    with engine.begin() as conn:
        for table, col, decl in _COLUMN_ALTERS:
            if _has_column(conn, dialect, table, col):
                continue
            conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def _has_column(conn, dialect: str, table: str, col: str) -> bool:
    if dialect == "sqlite":
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
        return col in {r[1] for r in rows}
    if dialect == "mysql":
        rows = conn.exec_driver_sql(
            f"SHOW COLUMNS FROM {table} LIKE '{col}'"
        ).fetchall()
        return bool(rows)
    return True
