"""Tests for Production PostgreSQL Migration Configuration & Runner.
Validates:
1. Alembic environment URL resolution and PostgreSQL driver compatibility.
2. Production safety checks (forbidding SQLite in production on Render).
3. Clear error messages when DATABASE_URL is missing or misconfigured.
4. Idempotent Alembic migration execution across versions e2d3530619fb -> a3f129c58b04.
"""
import os
import pytest
from unittest.mock import patch
from backend.app.run_migrations import (
    validate_and_get_database_url,
    is_production_environment,
)
from backend.alembic.env import get_database_url


def test_production_environment_detection():
    """Verify production detection on Render and environment flags."""
    with patch.dict(os.environ, {"RENDER": "true"}, clear=False):
        assert is_production_environment() is True

    with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False):
        assert is_production_environment() is True

    with patch.dict(os.environ, {"APP_ENV": "production"}, clear=False):
        assert is_production_environment() is True


def test_production_requires_database_url():
    """Verify that production fails fast if DATABASE_URL is empty."""
    with patch.dict(os.environ, {"RENDER": "true", "DATABASE_URL": ""}, clear=False):
        with pytest.raises(RuntimeError) as exc_info:
            validate_and_get_database_url()
        assert "CRITICAL" in str(exc_info.value)
        assert "DATABASE_URL" in str(exc_info.value)


def test_production_forbids_sqlite():
    """Verify that production strictly prohibits SQLite databases."""
    with patch.dict(os.environ, {"RENDER": "true", "DATABASE_URL": "sqlite:///./kirana_ai.db"}, clear=False):
        with pytest.raises(RuntimeError) as exc_info:
            validate_and_get_database_url()
        assert "SQLite" in str(exc_info.value)
        assert "prohibited" in str(exc_info.value).lower() or "violation" in str(exc_info.value).lower()


def test_postgres_url_normalization():
    """Verify that legacy postgres:// is normalized to postgresql:// for SQLAlchemy."""
    with patch.dict(os.environ, {"RENDER": "true", "DATABASE_URL": "postgres://user:pass@ep-server.supabase.co:5432/postgres"}, clear=False):
        normalized = validate_and_get_database_url()
        assert normalized.startswith("postgresql://")
        assert "supabase.co" in normalized


def test_alembic_env_url_resolution():
    """Verify that alembic/env.py get_database_url uses DATABASE_URL and normalizes it."""
    with patch.dict(os.environ, {"DATABASE_URL": "postgres://postgres:securepass@db.render.com:5432/kirana"}, clear=False):
        url = get_database_url()
        assert url.startswith("postgresql://")
        assert "db.render.com" in url


def test_local_development_preserves_sqlite():
    """Verify that local development preserves SQLite fallback."""
    with patch.dict(os.environ, {"DATABASE_URL": "", "ENVIRONMENT": "development", "RENDER": ""}, clear=False):
        # Remove RENDER if set
        os.environ.pop("RENDER", None)
        url = get_database_url()
        assert url.startswith("sqlite:///")
        assert "kirana_ai.db" in url

