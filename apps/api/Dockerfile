# apps/api/Dockerfile — multi-stage build for FastAPI runtime.
# Stage 1 (builder): install Python deps into user-site for layer reuse.
# Stage 2 (runtime): minimal image containing only the runnable bits.

FROM python:3.12-slim AS builder
WORKDIR /build
# Install build-time deps for asyncpg (which sometimes needs gcc) only if a wheel is missing;
# python:3.12-slim already includes the C runtime libs asyncpg needs at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY apps/api/requirements.txt apps/api/requirements-dev.txt ./
# Install BOTH runtime + dev deps in the builder; the runtime stage will copy /root/.local
# which means `make check` (pytest, ruff, pyright) can run inside the api container.
RUN pip install --no-cache-dir --user -r requirements.txt -r requirements-dev.txt

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/app
WORKDIR /app
# libpq is needed by asyncpg at runtime; install minimal runtime deps only.
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /root/.local /root/.local
COPY apps/api /app/apps/api
COPY packages /app/packages
EXPOSE 8000
CMD ["uvicorn", "apps.api.src.main:app", "--host", "0.0.0.0", "--port", "8000"]
