from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.persistence.db import get_db
from app.persistence.models import User
from app.services import auth as auth_svc


@dataclass
class AuthUser:
    user: User | None
    via: str  # jwt | api_key
    role: str


async def require_auth(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AuthUser:
    # Prefer JWT when present so logged-in users are identifiable.
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if token:
        try:
            payload = auth_svc.decode_token(token)
            user_id = str(payload.get("sub") or "")
            user = db.get(User, user_id) if user_id else None
            if user and user.status == "active":
                return AuthUser(user=user, via="jwt", role=user.role)
        except jwt.PyJWTError:
            pass
        # Invalid JWT still allowed to fall through to API key (local/CI).

    configured = (settings.api_key or "").strip()
    if configured:
        if x_api_key == configured:
            return AuthUser(user=None, via="api_key", role="api-key")
    elif x_api_key:
        return AuthUser(user=None, via="api_key", role="api-key")

    raise HTTPException(status_code=401, detail="authentication required")


# Back-compat alias used by existing routers
require_api_key = require_auth


async def get_current_user(auth: AuthUser = Depends(require_auth)) -> AuthUser:
    return auth
