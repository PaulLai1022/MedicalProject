"""Seed data — create the demo user and Case A on first launch."""

import logging
from pathlib import Path

from app.infra.db import SessionLocal
from app.infra.models import User
from app.infra.repositories import user_repo, case_repo
from app.services import generation_service

logger = logging.getLogger(__name__)

# Seed assets live under backend/app/seed_data/ (shipped alongside code / image)
_SEED_DIR = Path(__file__).resolve().parent.parent / "seed_data"
_ER_NOTES_A = _SEED_DIR / "case_a_er_notes.txt"
_HP_A = _SEED_DIR / "case_a_hp.txt"


def seed_if_empty() -> None:
    """If the users table is empty, create the demo user and pre-generate Case A."""
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count > 0:
            logger.info("Users already exist; skipping seed")
            return

        logger.info("Database is empty; seeding demo data...")

        # Create the demo user
        demo_user = user_repo.create(db, "demo@example.com", "demo1234")
        logger.info("Created demo user: %s", demo_user.email)

        # Load Case A raw text
        raw_text = _load_case_a_text()
        if not raw_text:
            logger.warning("Could not load Case A text; skipping case creation")
            return

        # Create Case A
        case = case_repo.create_case(db, demo_user.id, raw_text)
        logger.info("Created Case A: %s", case.id)

        # Pre-generate the structured output
        try:
            generation_service.run(db, case.id)
            logger.info("Case A structured generation completed")
        except Exception as e:
            logger.warning("Case A generation failed (LLM may not be configured): %s", str(e))

    except Exception as e:
        logger.error("Seed failed: %s", str(e))
        db.rollback()
    finally:
        db.close()


def _load_case_a_text() -> str:
    """Load and concatenate Case A's ER Notes and H&P text."""
    parts = []
    for path in [_ER_NOTES_A, _HP_A]:
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))
        else:
            logger.warning("File not found: %s", path)
    return "\n\n".join(parts)
