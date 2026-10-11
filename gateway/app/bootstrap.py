from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.persistence.models import EngineProfile


def seed_default_engine(db: Session) -> None:
    exists = db.query(EngineProfile).filter(EngineProfile.name == "default").first()
    if exists:
        # keep URL; align display model for DeepSeek engine
        if exists.model in ("", "gpt-4o-mini"):
            exists.model = "deepseek-chat"
            exists.vendor = "deepseek"
            db.commit()
        return
    db.add(
        EngineProfile(
            name="default",
            engine_base_url=settings.engine_default_url,
            model="deepseek-chat",
            vendor="deepseek",
        )
    )
    db.commit()
