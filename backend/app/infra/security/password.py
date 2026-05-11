"""Password hashing and verification — bcrypt with cost factor 12."""

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(plain: str) -> str:
    """Hash a plaintext password into a bcrypt string."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True iff the plaintext password matches the stored hash."""
    return _pwd_context.verify(plain, hashed)
