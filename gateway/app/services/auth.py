from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.persistence.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(password, password_hash)
    except Exception:  # noqa: BLE001
        return False


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=max(1, settings.jwt_expire_hours))
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def seed_admin(db: Session) -> None:
    username = (settings.seed_admin_user or "admin").strip()
    if not username:
        return
    if get_user_by_username(db, username):
        return
    row = User(
        username=username,
        email="",
        password_hash=hash_password(settings.seed_admin_password or "admin123"),
        role="admin",
        status="active",
    )
    db.add(row)
    db.commit()
