from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import AuthUser, get_current_user, require_auth
from app.config import settings
from app.persistence.db import get_db
from app.persistence.models import User
from app.services import auth as auth_svc

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    email: str = ""


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    email: str = ""
    role: str

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if not settings.allow_register:
        raise HTTPException(403, "registration disabled")
    username = body.username.strip()
    if auth_svc.get_user_by_username(db, username):
        raise HTTPException(400, "username already exists")
    row = User(
        username=username,
        email=(body.email or "").strip(),
        password_hash=auth_svc.hash_password(body.password),
        role="user",
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    token = auth_svc.create_access_token(row)
    return TokenOut(access_token=token, user=UserOut.model_validate(row))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    row = auth_svc.get_user_by_username(db, body.username.strip())
    if not row or row.status != "active" or not auth_svc.verify_password(body.password, row.password_hash):
        raise HTTPException(401, "invalid username or password")
    token = auth_svc.create_access_token(row)
    return TokenOut(access_token=token, user=UserOut.model_validate(row))


@router.get("/me", response_model=UserOut, dependencies=[Depends(require_auth)])
def me(user: AuthUser = Depends(get_current_user)):
    if not user.user:
        # API-key auth without user — return synthetic
        return UserOut(id="api-key", username="api-key", email="", role="admin")
    return UserOut.model_validate(user.user)


@router.get("/users", response_model=list[UserOut], dependencies=[Depends(require_auth)])
def list_users(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    if user.role not in ("admin", "api-key"):
        raise HTTPException(403, "admin only")
    return db.query(User).order_by(User.created_at.desc()).all()
