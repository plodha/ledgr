# Makefile — PRANAV Phase 0 developer interface.
# Run from repo root. All targets wrap docker compose with the Phase 0 compose file + .env.
#
# Quickstart:
#   cp .env.example .env
#   make dev       # boots 4 containers
#   make migrate   # (in a second terminal) applies Alembic baseline
#   make check     # runs lints + typechecks + tests (inside containers)
#
# NOTE: `make shell-db` uses POSTGRES_USER=pranav by default. This patches the legacy
# pre-rename example in CLAUDE.md per RESEARCH.md Assumption A5 (project renamed 2026-05-23).

.PHONY: dev down migrate check check-api check-web shell-api shell-db help

# Default target: print help
.DEFAULT_GOAL := help

COMPOSE := docker compose -f docker/docker-compose.yml --env-file .env

help:
	@echo "PRANAV Makefile targets:"
	@echo "  make dev          - Build and start all 4 containers (postgres, api, web, adminer)"
	@echo "  make down         - Stop and remove containers (postgres_data volume persists)"
	@echo "  make migrate      - Run Alembic upgrade head inside the api container"
	@echo "  make check        - Run all lints + typechecks + tests (api + web)"
	@echo "  make check-api    - Run only api checks (ruff + pyright + pytest)"
	@echo "  make check-web    - Run only web checks (tsc --noEmit + eslint)"
	@echo "  make shell-api    - Open a bash shell in the api container"
	@echo "  make shell-db     - Open a psql session against the postgres container (user: pranav)"

dev:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

migrate:
	$(COMPOSE) exec api alembic -c packages/db/alembic.ini upgrade head

check: check-api check-web

check-api:
	$(COMPOSE) exec api sh -c "ruff check . && ruff format --check . && pyright && pytest"

check-web:
	$(COMPOSE) exec web sh -c "pnpm tsc --noEmit && pnpm lint"

shell-api:
	$(COMPOSE) exec api bash

shell-db:
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-pranav} -d $${POSTGRES_DB:-pranav}
