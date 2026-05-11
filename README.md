# Clinical Note Structuring Tool

A full-stack web application that transforms unstructured clinical notes (ER notes, H&P notes) into **structured summaries** and an **admission-supporting Revised HPI**.

## Live Demo

- Frontend: _TBD — add deployed URL here_
- Backend API docs: _TBD — add deployed URL here_

**Demo credentials** (seeded on first boot when `SEED_DEMO=true`):

| Field | Value |
|---|---|
| Email | `demo@example.com` |
| Password | `demo1234` |

## Architecture

```
Frontend (React + Vite + TypeScript)
        │ HTTP/JSON + JWT
Backend (FastAPI + Python 3.11)
  ├── LLMExtractor      (LLM, schema-constrained, source_span tracking)
  ├── RegexVerifier     (regex cross-check against source text)
  ├── RulesEngine       (MCG M-130 Diabetes JSON + predicate DSL)
  ├── NarrativeComposer (LLM, six-sentence Revised HPI)
  └── SQLite3 (data/app.db)
```

The pipeline is **LLM-first extraction, regex-verified, rules-authoritative**:

1. **LLMExtractor** reads unstructured clinical text and emits a Pydantic-validated `ExtractedFactsSchema` (labs, vitals, symptoms, medications, imaging findings, interventions, history). Every fact carries a `source_span` pointing back to the original text.
2. **RegexVerifier** cross-checks numeric labs/vitals against the source text using clinical regex patterns. Inconsistent values (e.g. LLM hallucinated `glucose=350` but the note only says `glucose=412`) are marked `verification_failed` and treated by the rules engine as if the field were missing. Temperature is unit-aware (°F ↔ °C).
3. **RulesEngine** is the **single source of truth for `disposition`**. It evaluates verified facts against MCG M-130 Diabetes rules and returns hits with verbatim citations. The LLM is not permitted to override the disposition.
4. **NarrativeComposer** produces a six-sentence Revised HPI from the verified facts and rule hits, with each sentence's `reasonGuideline` constrained to MCG citations actually emitted by the rules engine.

When the LLM is unavailable or its response cannot be schema-validated even after one self-repair attempt, the pipeline falls back to a deterministic rule-based summary so the API still returns a usable structured response.

## Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI | Type-safe, auto-generated OpenAPI, async-ready |
| ORM | SQLAlchemy 2 + Alembic | Industry standard, explicit migrations |
| Database | SQLite3 | Zero-configuration, works out of the box for a take-home |
| LLM SDK | OpenAI Python SDK | Works with DeepSeek / any OpenAI-compatible endpoint |
| LLM extractor | Pydantic-schema-constrained JSON output | Generalizes to free-text and any disease domain |
| Regex verifier | Hand-authored clinical patterns | Catches LLM numeric hallucinations; deterministic |
| Rules engine | Hand-authored JSON + predicate DSL | Auditable, citable, zero runtime dependency |
| Frontend | React 18 + Vite + TypeScript | Fast cold start, mature ecosystem |
| Styling | Tailwind CSS | Rapid, consistent UI without custom design system |
| State | TanStack Query + Zustand | Server state + lightweight client state |

## Running Locally

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate   # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
cp .env.example .env     # then fill in LLM_API_KEY, JWT_SECRET, etc.
alembic upgrade head
uvicorn app.main:app --reload --port 8200
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Backend OpenAPI docs: `http://localhost:8200/docs`.

### One-command Docker

```bash
docker compose up --build
```

Frontend on port 80, backend on 8200. Nginx inside the frontend container reverse-proxies `/api` to the backend service.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `LLM_BASE_URL` | LLM API endpoint | _(empty)_ |
| `LLM_API_KEY` | LLM API key | _(empty)_ |
| `LLM_MODEL` | Model name | `deepseek-v4-flash` |
| `LLM_USE_STRICT_SCHEMA` | Use `json_schema` strict mode. Set to `false` for endpoints that reject strict mode (e.g. DeepSeek) to avoid a wasted 400 round-trip per LLM call. The client also auto-falls back at runtime if the endpoint rejects the request. | `false` (repo default, tuned for DeepSeek) |
| `LLM_LOG_ENABLED` | Persist LLM request/response for debugging | `true` |
| `JWT_SECRET` | JWT signing key (≥ 32 bytes in production) | _(dev placeholder)_ |
| `JWT_EXPIRE_MINUTES` | Token lifetime | `1440` |
| `DATABASE_URL` | SQLite path | `sqlite:///./data/app.db` |
| `FRONTEND_ORIGIN` | CORS allow-origin for the frontend | `http://localhost:5173` |
| `LOG_LEVEL` | Python logging level | `INFO` |
| `SEED_DEMO` | Seed a demo user and sample case on startup | `true` |

## How the Clinical Note Is Structured

A four-stage **LLM-first + regex-verified + rules-authoritative** pipeline:

1. **LLMExtractor** — sends the raw note to the LLM with a Pydantic schema (`ExtractedFactsSchema`) and a system prompt that forbids fabrication. Output includes `chief_complaint`, `hpi_summary`, `suspected_conditions`, plus typed lists of `labs`, `vitals`, `symptoms`, `medications`, `imaging_findings`, `interventions`, `history`. Every fact carries a `source_span` (start/end character offsets in the original note).
2. **RegexVerifier** — for each numeric lab/vital, runs the corresponding clinical regex on the source text around the reported `source_span`. Three outcomes: `verified` (regex value matches LLM value within 2% relative tolerance), `failed` (regex finds a different number — likely LLM hallucination), or `unverifiable` (no regex pattern for that field, or no hit in the window). Temperature is unit-aware: a regex match like `Temp: 98 F` is normalized to °C before comparison.
3. **RulesEngine** — evaluates verified facts against `mcg_diabetes.json` (MCG M-130). Facts marked `verification_failed` are treated as missing. Produces `hits[]` (with verbatim citations and clinical explanations) and a final `Disposition`.
4. **NarrativeComposer** — composes a six-sentence Revised HPI from the verified facts and rule hits, with `reasonGuideline` constrained to citations the rules engine actually emitted.

Each output field carries an `origin` flag (`machine` | `user`) so the UI can visually distinguish machine-generated content from user edits.

### Output schema strictness (Pydantic档 B)

Both the extractor and composer outputs use Pydantic schemas where every field is **required but value-permissive**: the LLM must include each field, but values may be `""` or `[]` if no fact of that type exists in the note. This catches "LLM silently dropped a field" failures that would otherwise be hidden by Pydantic defaults.

### LLM output reliability (4-layer recovery)

1. **Source-level constraint** — `response_format={"type":"json_schema", "strict":true}`. Endpoints that don't support strict mode (e.g. some DeepSeek deployments) auto-fall back to `json_object` mode; the system prompt also includes a complete field checklist so the LLM produces all required keys without schema injection.
2. **Pydantic strict validation** —档 B schema rejects missing fields rather than filling with defaults.
3. **One-shot LLM self-repair** — if validation fails, the original prompt + bad response + error message are re-submitted to the LLM with a single retry (`repair_count` is recorded on the call result).
4. **Deterministic fallback** — if all else fails, the rules engine's hits are formatted into a one-sentence summary so the API never returns an empty Revised HPI.

## How the Revised HPI Is Generated

Fixed six-sentence skeleton:

1. Presentation (onset and chief complaint)
2. Objective vitals (abnormal vital signs)
3. Objective labs (values with units, must match the source text verbatim)
4. Diagnostic characterization (primary diagnosis and risk factors)
5. ER interventions already delivered
6. Integrated decision, **citing the MCG rule(s)** that support the Disposition

**Authority of Disposition**: the rules engine is the single source of truth. The LLM is not permitted to produce a Disposition field on its own.

## How Uncertainty / Missing Information Is Handled

Core diagnostic fields are declared in the ruleset JSON (`mcg_diabetes.json` → `core_fields`), so different guidelines can self-describe what counts as "core" without code changes. For MCG M-130 the core fields are: `glucose`, `ketones`, `acidosis_marker` (any of pH / bicarbonate / CO2).

A field is considered "missing" if the LLM extractor produced no fact for it OR the regex verifier marked it `verification_failed`. Decision branches (evaluated in order):

1. All core fields missing → `disposition = Unknown` (path `5.1_ALL_CORE_MISSING`)
2. Missing count ≥ `missing_threshold_unknown` (default 2) → `disposition = Unknown` (path `5.2_TWO_OR_MORE_CORE_MISSING`)
3. Any Admit-category rule fires → `disposition = Admit` (path `5.3_ADMIT_RULE_HIT`); still-missing fields go into `uncertainties`
4. Only Observation-category rules fire → `disposition = Observe` (path `5.4_OBSERVATION_ONLY`)
5. No rule fires → `disposition = Discharge` (path `5.5_NO_RULE_HIT`)

Missing items, verifier warnings, and MCG rule hits are all surfaced in the UI so the reviewer can see exactly why the system made its recommendation.

## AI / Tool Usage Disclosure

AI tools were used during development in the following ways:

- **Code generation**: project scaffolding, ORM models, API routes, and React components were drafted with AI assistance. All generated code was reviewed and adjusted manually.
- **LLM prompt design**: the `LLMExtractor` prompt (in `backend/app/core/extractor/llm_extractor.py`) and the `NarrativeComposer` prompt (in `backend/app/core/llm/prompts.py`) were hand-authored. Both include explicit constraints against hallucination, mandatory `source_span` traceability, a complete field checklist, and a pre-output verification checklist so the LLM produces schema-correct output even when the endpoint does not support `json_schema` strict mode.
- **MCG rule set**: `backend/app/rules_data/mcg_diabetes.json` was hand-authored against the MCG M-130 guideline, not AI-generated.
- **Regex patterns**: clinical patterns in `backend/app/core/extractor/patterns.py` were hand-authored. They are no longer the primary extraction path — they now serve `RegexVerifier` to detect numeric inconsistencies between LLM output and the original note.
- **Verification**: the full pipeline was exercised end-to-end against Case A and Case B via `test/curl_test.py` and `test/verify_cases.py`. The LLM-extracted facts and the generated Revised HPI were compared against the provided human-optimized Revised HPI to check fact capture, admission reasoning, and structural consistency.

### Production Notes

- Set `LLM_LOG_ENABLED=false` in production to avoid persisting PHI in logs.
- Raw clinical text should be de-identified before storage.
- `JWT_SECRET` must be a strong random value (≥ 32 bytes).
- If your LLM endpoint rejects `response_format={"type":"json_schema"}` (DeepSeek currently does), leave `LLM_USE_STRICT_SCHEMA=false` — this is the repo default. Keeping it `true` against such an endpoint costs one wasted 400 round-trip per LLM call before the client auto-falls back to `json_object`. Set it to `true` only on endpoints (e.g. OpenAI GPT-4o, Azure OpenAI newer deployments) that advertise strict `json_schema` support.

## If I Had More Time

- **Multi-ruleset routing** — the `core_fields` and `missing_threshold_unknown` metadata are already in the ruleset JSON, ready for additional guidelines (e.g. MCG M-180 GI Surgery for diverticulitis, MCG M-460 Heart Failure). Adding a new ruleset would require no extractor or engine changes — only a new JSON file plus a small router that selects the active ruleset based on `suspected_conditions`.
- **RAG-backed guidelines** — vectorize the full MCG corpus so the LLM can retrieve more than a single ruleset
- **Multilingual input** — extractor support for Chinese clinical notes (the LLM-first design already handles this; only prompt/system-message localization is needed)
- **Richer regex verifier** — extend unit-aware comparison beyond temperature (creatinine mg/dL ↔ µmol/L, glucose mg/dL ↔ mmol/L for cases the normalizer doesn't cover)
- **Time-series facts** — preserve repeat measurements with timestamps so "glucose 412 on arrival, 280 after treatment" is not collapsed into a single value
- **RBAC** — role-based access (physician / reviewer / admin)
- **HIPAA de-identification** — automatic detection and redaction of PHI (names, MRN, dates)
- **Infrastructure** — Kubernetes + PostgreSQL + Redis cache
- **Automated testing** — property-based tests for the verifier and rules engine
- **Real-time collaboration** — WebSocket-backed concurrent editing on the same case
- **Audit trail** — complete operation audit log

## Project Structure

```
.
├── backend/
│   ├── alembic/          schema migrations
│   ├── app/
│   │   ├── api/          HTTP routes
│   │   ├── core/         extractor / rules / llm
│   │   ├── infra/        db, models, repositories, security
│   │   ├── rules_data/   MCG JSON rule sets
│   │   ├── schemas/      Pydantic I/O schemas
│   │   └── services/     use-case orchestration
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/          API clients and types
│   │   ├── components/   UI components (case, form, ui)
│   │   ├── pages/        routed pages
│   │   └── store/        Zustand stores
│   ├── Dockerfile
│   ├── nginx.conf
│   └── eslint.config.js
├── docker-compose.yml
└── README.md
```
