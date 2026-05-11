"""FastAPI application entrypoint — wires middleware, routers, and lifecycle events."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize logging, seed data, etc. on startup."""
    settings = get_settings()
    setup_logging(settings.log_level)

    # Seed demo data (only when SEED_DEMO=true)
    if settings.seed_demo:
        from app.infra.seed import seed_if_empty  # noqa: E402
        seed_if_empty()

    yield


def create_app() -> FastAPI:
    """Factory that creates and configures the FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title="Clinical Note Structuring Tool",
        description="Convert unstructured clinical notes into a structured summary and Revised HPI",
        version="0.1.0",
        openapi_url="/openapi.json",
        docs_url="/docs",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global error handlers
    from app.api.errors import register_error_handlers
    register_error_handlers(app)

    # Register routers
    from app.api.auth import router as auth_router
    from app.api.cases import router as cases_router
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(cases_router, prefix="/api/cases", tags=["cases"])

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8200, reload=True)
