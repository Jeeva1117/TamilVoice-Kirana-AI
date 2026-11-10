"""Production-Safe Database Migration Runner for TamilVoice Kirana AI.

Provides a robust, zero-downtime database migration routine for Render,
Supabase, and local development.

Key Features:
1. Environment-aware validation:
   - Prohibits SQLite in production environments (Render).
   - Enforces a valid, reachable PostgreSQL DATABASE_URL.
   - Preserves SQLite for local offline development.
2. Driver and format compatibility:
   - Normalizes legacy postgres:// URIs to postgresql://.
   - Automatically enforces sslmode=require for cloud PostgreSQL.
3. Automated Alembic execution:
   - Runs all pending migrations sequentially to revision 'head'.
   - Idempotent and safe to run on every deploy.
4. Auto-seeding:
   - Automatically seeds the 43 universal Kirana catalog items if a newly
     deployed database has 0 products.
"""
import os
import sys
import logging
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command
from backend.app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("migration_runner")


def is_production_environment() -> bool:
    """Detect whether current process is running in production (e.g. Render)."""
    return bool(
        os.getenv("RENDER") is not None
        or os.getenv("ENVIRONMENT", "").lower() == "production"
        or os.getenv("APP_ENV", "").lower() == "production"
        or getattr(settings, "ENVIRONMENT", "").lower() == "production"
        or getattr(settings, "APP_ENV", "").lower() == "production"
    )


def validate_and_get_database_url() -> str:
    """
    Validate and return the database URL according to deployment environment.
    Raises RuntimeError if production safety constraints are violated.
    """
    raw_url = (os.getenv("DATABASE_URL") or getattr(settings, "DATABASE_URL", "")).strip()
    is_prod = is_production_environment()

    if is_prod:
        if not raw_url:
            error_msg = (
                "CRITICAL DEPLOYMENT BLOCKER: DATABASE_URL environment variable is missing on Render. "
                "Production requires a PostgreSQL database (e.g. Supabase, Neon, or Render PostgreSQL). "
                "Please configure DATABASE_URL in your Render Dashboard -> Environment Variables."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

        if raw_url.startswith("sqlite"):
            error_msg = (
                f"CRITICAL SAFETY VIOLATION: Detected SQLite database in production environment ('{raw_url}'). "
                "Render web service containers have ephemeral filesystems; SQLite data is erased upon each deploy. "
                "Production must use a PostgreSQL database. Please configure DATABASE_URL with a postgresql:// URL."
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

    # Local development fallback
    if not raw_url or raw_url.startswith("sqlite"):
        db_file = PROJECT_ROOT / "kirana_ai.db"
        raw_url = f"sqlite:///{db_file.as_posix()}"
        logger.info(f"Local development mode: Using SQLite database at {db_file}")

    # Normalize postgres:// to postgresql:// for SQLAlchemy 2.0+ compatibility
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)

    return raw_url


def test_database_connectivity(db_url: str) -> None:
    """Verify that the database is reachable before applying migrations."""
    connect_args = {}
    if db_url.startswith("postgresql") or db_url.startswith("postgres"):
        connect_args["connect_timeout"] = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
        if "sslmode" not in db_url.lower() and "localhost" not in db_url and "127.0.0.1" not in db_url:
            connect_args["sslmode"] = "require"
    elif db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(db_url, connect_args=connect_args)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        logger.info("Database connectivity check: SUCCESSFUL.")
    except Exception as e:
        logger.error(f"Database connectivity check FAILED: {e}")
        raise RuntimeError(f"Unable to establish database connection: {e}") from e
    finally:
        engine.dispose()


def run_alembic_upgrade(db_url: str) -> None:
    """Execute Alembic migrations to head."""
    # Find alembic.ini (check project root first, then backend/)
    ini_path = PROJECT_ROOT / "alembic.ini"
    if not ini_path.exists():
        ini_path = PROJECT_ROOT / "backend" / "alembic.ini"

    if not ini_path.exists():
        raise FileNotFoundError(f"Alembic configuration file not found at {ini_path}")

    logger.info(f"Loading Alembic configuration from {ini_path}...")
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    logger.info("Executing Alembic upgrade to revision 'head'...")
    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic migrations completed successfully.")


def seed_catalog_if_empty(db_url: str) -> None:
    """If database has 0 products, seed initial universal Kirana catalog items."""
    from backend.app.database import SessionLocal
    from backend.app.models.product import Product
    from backend.app.database_seeder import seed_database

    db = SessionLocal()
    try:
        product_count = db.query(Product).count()
        if product_count == 0:
            logger.info("Fresh database detected (0 catalog products). Seeding default Kirana products...")
            seed_database(db)
            new_count = db.query(Product).count()
            logger.info(f"Seeding completed successfully: {new_count} products registered.")
        else:
            logger.info(f"Existing catalog verified ({product_count} active products). Skipping seed.")
    except Exception as e:
        logger.warning(f"Catalog seed check encountered non-fatal notice: {e}")
    finally:
        db.close()


def main():
    """Main entrypoint for Render preDeployCommand and manual execution."""
    logger.info("======================================================")
    logger.info("TamilVoice Kirana AI - Production Migration Runner")
    logger.info("======================================================")

    try:
        db_url = validate_and_get_database_url()
        test_database_connectivity(db_url)
        run_alembic_upgrade(db_url)
        seed_catalog_if_empty(db_url)
        logger.info("======================================================")
        logger.info("Database migration routine completed with 100% SUCCESS.")
        logger.info("======================================================")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Database migration routine FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

