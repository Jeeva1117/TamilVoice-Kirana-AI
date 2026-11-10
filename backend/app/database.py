"""Database Connection & Session Management: SQLite (Local) and PostgreSQL (Production)."""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config import settings

raw_db_url = (settings.DATABASE_URL or "sqlite:///./kirana_ai.db").strip()

# PostgreSQL URL normalization: Render / Railway / Supabase / Neon postgres:// -> postgresql://
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

is_sqlite = raw_db_url.startswith("sqlite")
is_postgres = raw_db_url.startswith("postgresql")

is_production = (
    os.getenv("RENDER") is not None
    or os.getenv("ENVIRONMENT", "").lower() == "production"
    or os.getenv("APP_ENV", "").lower() == "production"
    or getattr(settings, "ENVIRONMENT", "").lower() == "production"
    or getattr(settings, "APP_ENV", "").lower() == "production"
)

if is_production and is_sqlite:
    raise RuntimeError(
        "CRITICAL DATABASE ERROR: Running with SQLite in production on Render is prohibited. "
        "Render web service containers have ephemeral storage; all data will be lost on container restart. "
        "Please configure DATABASE_URL in your Render Environment Variables with your PostgreSQL connection string."
    )

engine_kwargs = {
    "echo": False,
    "future": True,
}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Production PostgreSQL connection pooling & pre-ping health checks (Supabase / Render)
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_recycle"] = 300

    # Supabase / cloud SSL configuration
    connect_args = {}
    if "sslmode" not in raw_db_url.lower() and "localhost" not in raw_db_url and "127.0.0.1" not in raw_db_url:
        connect_args["sslmode"] = "require"
    if connect_args:
        engine_kwargs["connect_args"] = connect_args

engine = create_engine(raw_db_url, **engine_kwargs)

# Enable SQLite foreign key constraint enforcement only on SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if is_sqlite:
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        except Exception:
            pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def get_db():
    """Dependency yields a database session and safely closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
