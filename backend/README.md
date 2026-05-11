# Backend — Clinical Note Structuring Tool

Python FastAPI backend exposing a REST API.

## Getting started

```bash
# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and fill in LLM_API_KEY, JWT_SECRET, etc.

# Database migrations
alembic upgrade head

# Start the dev server
uvicorn app.main:app --reload --port 8200
```

## API documentation

After startup, open http://localhost:8200/docs for the Swagger UI.

## Directory layout

- `app/api/` — route layer
- `app/services/` — business services
- `app/core/` — domain layer (Extractor / RulesEngine / LLM)
- `app/infra/` — infrastructure (DB / Repositories / Security)
- `app/schemas/` — Pydantic request/response models
- `app/rules_data/` — MCG rules JSON
- `alembic/` — database migrations
- `data/` — SQLite database files (gitignored)

## Debug scripts

Located under `test/` at the repo root:
- `test/db_smoke.py` — verify the database schema
- `test/extractor_smoke.py` — smoke-test the extractor
- `test/rules_smoke.py` — exercise rules-engine branches
