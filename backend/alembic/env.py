"""Alembic Environment Configuration for TamilVoice Kirana AI.
Supports dual-database architecture:
- SQLite for local offline development.
- PostgreSQL (Supabase / Render) for cloud production.
Enforces strict validation in production: prohibits SQLite and requires DATABASE_URL.
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool, create_engine
from alembic import context

# Setup paths to ensure backend package can be imported reliably
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = getattr(context, "config", None)

# Interpret the config file for Python logging.
if config is not None and config.config_file_name is not None:
    fileConfig(config.config_file_name)

from backend.app.database import Base
import backend.app.models  # Ensures all models are registered
from backend.app.config import settings

target_metadata = Base.metadata


def get_database_url() -> str:
    """
    Resolve and validate the database connection URL for migrations.
    
    Order of precedence:
    1. CLI argument (-x db_url=... or -x url=...)
    2. Environment variable DATABASE_URL
    3. settings.DATABASE_URL
    4. Local SQLite fallback (kirana_ai.db at project root)
    
    Safety Rules:
    - In production (Render, ENVIRONMENT=production, APP_ENV=production):
      Strictly forbids SQLite. Requires a valid PostgreSQL URL.
    - Normalizes legacy postgres:// to postgresql:// for SQLAlchemy 2.0+ compatibility.
    """
    # 1. Check CLI -x arguments
    raw_url = ""
    if hasattr(context, "get_x_argument"):
        try:
            x_args = context.get_x_argument(as_dictionary=True)
            raw_url = x_args.get("db_url") or x_args.get("url") or ""
        except Exception:
            pass

    # 2. Check environment variable & settings
    if not raw_url or not str(raw_url).strip():
        raw_url = os.getenv("DATABASE_URL") or getattr(settings, "DATABASE_URL", "")

    raw_url = str(raw_url).strip() if raw_url else ""

    # Determine whether running in a production deployment
    is_production = (
        os.getenv("RENDER") is not None
        or os.getenv("ENVIRONMENT", "").lower() == "production"
        or os.getenv("APP_ENV", "").lower() == "production"
        or getattr(settings, "ENVIRONMENT", "").lower() == "production"
        or getattr(settings, "APP_ENV", "").lower() == "production"
    )

    # Production validation
    if is_production:
        if not raw_url:
            raise RuntimeError(
                "CRITICAL MIGRATION ERROR: DATABASE_URL environment variable is required in production, "
                "but is missing or empty. Please set DATABASE_URL to a valid PostgreSQL connection string "
                "(e.g., Supabase, Neon, or Render PostgreSQL)."
            )
        if raw_url.startswith("sqlite"):
            raise RuntimeError(
                f"CRITICAL CONFIGURATION ERROR: Running migrations against SQLite in a production environment "
                f"is strictly prohibited (detected: '{raw_url}'). "
                "Render and production deployments must use a PostgreSQL database. "
                "Please configure DATABASE_URL with a valid postgresql:// connection string."
            )

    # Local development fallback
    if not raw_url or raw_url.startswith("sqlite"):
        db_file = PROJECT_ROOT / "kirana_ai.db"
        raw_url = f"sqlite:///{db_file.as_posix()}"

    # Normalize legacy postgres:// to postgresql:// for SQLAlchemy 2.0+ and psycopg2
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)

    return raw_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    config.set_main_option("sqlalchemy.url", url)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_database_url()
    config.set_main_option("sqlalchemy.url", url)

    connect_args = {}
    if url.startswith("postgresql") or url.startswith("postgres"):
        connect_args["connect_timeout"] = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
        if "sslmode" not in url.lower() and "localhost" not in url and "127.0.0.1" not in url:
            connect_args["sslmode"] = "require"
    elif url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if config is not None and hasattr(context, "is_offline_mode"):
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
