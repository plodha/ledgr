"""Application settings loaded from environment via pydantic-settings.

Source of truth for the env-var contract documented in repo-root
``.env.example`` (INFRA-06). The ``Settings`` class is the only place that
reads ``os.environ`` for runtime config — every other module imports
``get_settings()`` and consumes typed fields.

Fields without defaults (``DATABASE_URL``, ``SECRET_KEY``) MUST be provided
via the process environment; pydantic-settings will raise ``ValidationError``
on import if they are missing. This is intentional fail-fast behavior — the
app should refuse to boot without a database URL or signing secret.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime configuration backed by environment variables / ``.env``.

    See ``.env.example`` at the repo root for the canonical list of keys the
    Phase 0 stack expects.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    SECRET_KEY: str
    ENVIRONMENT: Literal["dev", "production", "test"] = "dev"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    APP_VERSION: str = "0.1.0"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse the comma-separated ``ALLOWED_ORIGINS`` env var into a list.

        Empty entries are dropped (so a trailing comma is harmless). Used by
        ``CORSMiddleware`` in ``main.py``; never wildcard with credentials.
        """
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide ``Settings`` singleton.

    Cached so every ``Depends(get_settings)`` and every module-level
    ``get_settings()`` call returns the same instance. The ``# type: ignore``
    is the documented escape hatch for pyright strict mode: ``Settings`` has
    required fields that pyright can't see come from the environment.
    """
    return Settings()  # type: ignore[call-arg]
