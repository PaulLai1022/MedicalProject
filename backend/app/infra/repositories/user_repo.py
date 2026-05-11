"""User repository layer."""

from sqlalchemy.orm import Session

from app.infra.models import User
from app.infra.security.password import hash_password


def get_by_email(db: Session, email: str) -> User | None:
    """Look up a user by email; return None if not found."""
    return db.query(User).filter(User.email == email).first()


def create(db: Session, email: str, plain_password: str) -> User:
    """Create and persist a new user."""
    user = User(email=email, password_hash=hash_password(plain_password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
