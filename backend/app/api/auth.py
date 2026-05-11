"""Authentication routes — /api/auth/*"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.infra.db import get_db
from app.infra.models import User
from app.schemas.auth import AuthResp, LoginReq, RegisterReq, UserOut
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=AuthResp, status_code=201)
def register(body: RegisterReq, db: Session = Depends(get_db)):
    return auth_service.register(db, body.email, body.password)


@router.post("/login", response_model=AuthResp)
def login(body: LoginReq, db: Session = Depends(get_db)):
    return auth_service.login(db, body.email, body.password)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut(id=current_user.id, email=current_user.email)


@router.post("/logout", status_code=204)
def logout():
    """Logout — the client simply discards the token; the server is stateless."""
    return None
