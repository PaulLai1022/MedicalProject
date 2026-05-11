"""JWT issuing and decoding — HS256."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import get_settings

_ALGORITHM = "HS256"


def create_access_token(user_id: str, email: str) -> str:
    """Issue a JWT whose payload contains sub(user_id), email, and exp."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode a JWT and return its payload dict. Raises JWTError if invalid/expired."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
