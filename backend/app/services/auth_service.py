"""Authentication service — registration and login logic."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.infra.repositories import user_repo
from app.infra.security.jwt import create_access_token
from app.infra.security.password import verify_password
from app.schemas.auth import AuthResp, UserOut


def register(db: Session, email: str, password: str) -> AuthResp:
    """Register a new user. Email conflict → 409."""
    existing = user_repo.get_by_email(db, email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "This email is already registered"},
        )
    user = user_repo.create(db, email, password)
    token = create_access_token(user.id, user.email)
    return AuthResp(accessToken=token, user=UserOut(id=user.id, email=user.email))


def login(db: Session, email: str, password: str) -> AuthResp:
    """Log in. Invalid credentials → 401."""
    user = user_repo.get_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Invalid email or password"},
        )
    token = create_access_token(user.id, user.email)
    return AuthResp(accessToken=token, user=UserOut(id=user.id, email=user.email))
