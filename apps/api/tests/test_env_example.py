"""Wave 0 test for INFRA-06: ``.env.example`` documents every required env var
that docker-compose interpolates and that ``Settings`` (Wave 1) reads.

This test does not depend on Wave 1 production code — it parses the
repo-root ``.env.example`` file directly — so it should go green
immediately after Task 1 of Plan 01 lands.
"""

from __future__ import annotations

from pathlib import Path


REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "SECRET_KEY",
        "ENVIRONMENT",
        "LOG_LEVEL",
        "ALLOWED_ORIGINS",
        "NEXT_PUBLIC_API_URL",
    }
)


def _repo_root() -> Path:
    # tests/test_env_example.py -> tests -> api -> apps -> <repo root>
    return Path(__file__).resolve().parents[3]


def test_env_example_documents_all_required_keys() -> None:
    env_example = _repo_root() / ".env.example"
    assert env_example.is_file(), f"missing .env.example at {env_example}"

    keys: set[str] = set()
    for raw_line in env_example.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if not key:
            continue
        keys.add(key)

    missing = REQUIRED_KEYS - keys
    assert not missing, f".env.example is missing required keys: {sorted(missing)}"
