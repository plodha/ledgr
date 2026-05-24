"""FastAPI application entrypoint.

Wires:
  - ``get_settings()`` -> typed runtime config
  - ``configure_logging(...)`` -> structlog (JSON in prod, console otherwise)
  - ``lifespan`` -> disposes the async engine on shutdown (engine is module-
    level in ``database.py``, so startup is implicit at import time)
  - ``CORSMiddleware`` -> origins from ``ALLOWED_ORIGINS`` env var (never
    wildcard while ``allow_credentials=True``, per CORS spec)
  - ``RequestContextMiddleware`` -> binds ``request_id`` to structlog
    contextvars for every HTTP request (added AFTER CORSMiddleware so
    request_id is bound for preflight responses too)
  - ``/health`` router (the only feature route allowed in Phase 0)

Phase 0 explicitly does NOT register any other routers, exception handlers,
or OpenAPI customizations — per CLAUDE.md "No feature routes beyond /health".
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import engine
from .logging_config import RequestContextMiddleware, configure_logging
from .modules.health.router import router as health_router

settings = get_settings()
configure_logging(environment=settings.ENVIRONMENT, level=settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Yield once (startup is implicit) and dispose the engine on shutdown.

    The async engine is created at module import in ``database.py``; the
    lifespan only needs to release the connection pool when the app stops.
    """
    yield
    await engine.dispose()


app = FastAPI(
    title="PRANAV API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pure ASGI middleware — binds request_id to structlog contextvars.
# Added AFTER CORSMiddleware so the context is established for every HTTP
# request including CORS preflight (OPTIONS) responses.
app.add_middleware(RequestContextMiddleware)

app.include_router(health_router, prefix="/health", tags=["health"])
