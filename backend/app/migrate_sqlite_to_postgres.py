"""SQLite to PostgreSQL Data Migration Script for TamilVoice Kirana AI.

Safely migrates all catalog, inventory, customer, sales, store settings, and
voice usage records from local SQLite (kirana_ai.db) to production PostgreSQL (Supabase).
Preserves IDs, timestamps, foreign keys, and resets PostgreSQL sequences.
"""
import sys
import os
import argparse
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

from backend.app.config import settings
from backend.app.database import Base
from backend.app.models.product import Product
from backend.app.models.customer import Customer
from backend.app.models.sale import Sale
from backend.app.models.sale_item import SaleItem
from backend.app.models.stock_movement import StockMovement
from backend.app.models.store_setting import StoreSetting
from backend.app.models.gnani_usage import GnaniApiUsage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migration")


def get_sqlite_engine(sqlite_path: str):
    """Create engine for source SQLite database."""
    if not os.path.isabs(sqlite_path):
        sqlite_path = os.path.abspath(sqlite_path)
    url = f"sqlite:///{sqlite_path}"
    logger.info(f"Connecting to source SQLite: {url}")
    return create_engine(url, connect_args={"check_same_thread": False})


def get_postgres_engine(postgres_url: str):
    """Create engine for target PostgreSQL database with SSL configuration."""
    raw_url = postgres_url.strip()
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)

    connect_args = {}
    if "sslmode" not in raw_url.lower() and "localhost" not in raw_url and "127.0.0.1" not in raw_url:
        connect_args["sslmode"] = "require"

    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
    }
    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    logger.info("Connecting to target PostgreSQL database...")
    return create_engine(raw_url, **engine_kwargs)


def migrate_table(sqlite_session, pg_session, model_cls, table_name: str, id_col: str = "id") -> int:
    """Migrate rows from SQLite session to PostgreSQL session for a given model."""
    sqlite_rows = sqlite_session.query(model_cls).order_by(getattr(model_cls, id_col).asc()).all()
    count = len(sqlite_rows)
    logger.info(f"Migrating {table_name}: found {count} rows in SQLite...")

    migrated = 0
    for row in sqlite_rows:
        # Check if already exists in PostgreSQL
        existing = pg_session.query(model_cls).filter(getattr(model_cls, id_col) == getattr(row, id_col)).first()
        if not existing:
            # Extract dictionary of model columns
            mapper = inspect(model_cls)
            data = {}
            for col in mapper.column_attrs:
                val = getattr(row, col.key)
                # Handle Decimal / Float conversions if needed
                if isinstance(val, Decimal):
                    val = float(val)
                data[col.key] = val

            new_obj = model_cls(**data)
            pg_session.add(new_obj)
            migrated += 1

    pg_session.commit()
    logger.info(f"  -> {table_name}: committed {migrated} new rows (total {count} present).")
    return count


def reset_postgres_sequences(pg_engine, tables: List[str]):
    """Reset PostgreSQL auto-increment sequences to max(id) to avoid duplicate key errors."""
    with pg_engine.connect() as conn:
        for t in tables:
            try:
                # Query sequence name and max id
                seq_query = text(f"SELECT pg_get_serial_sequence('{t}', 'id');")
                seq_name = conn.execute(seq_query).scalar()
                if seq_name:
                    max_id = conn.execute(text(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {t};")).scalar()
                    conn.execute(text(f"SELECT setval('{seq_name}', {max_id}, false);"))
                    conn.commit()
                    logger.info(f"Reset sequence for '{t}' -> next ID will be {max_id}")
            except Exception as e:
                logger.warning(f"Could not reset sequence for {t}: {e}")


def run_migration(sqlite_path: str, postgres_url: str, dry_run: bool = False):
    """Execute complete migration pipeline."""
    if not os.path.exists(sqlite_path):
        logger.error(f"Source SQLite database not found at: {sqlite_path}")
        sys.exit(1)

    sqlite_engine = get_sqlite_engine(sqlite_path)
    pg_engine = get_postgres_engine(postgres_url)

    # 1. Test connections
    with sqlite_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("Source SQLite connection verified.")

    with pg_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("Target PostgreSQL connection verified.")

    if dry_run:
        logger.info("DRY-RUN mode enabled. No data will be written.")
        return

    # 2. Ensure schema exists in PostgreSQL
    logger.info("Creating tables and foreign keys in PostgreSQL if not present...")
    Base.metadata.create_all(bind=pg_engine)
    logger.info("Target schema verified.")

    # 3. Create sessions
    SqliteSession = sessionmaker(bind=sqlite_engine)
    PgSession = sessionmaker(bind=pg_engine)

    sqlite_db = SqliteSession()
    pg_db = PgSession()

    try:
        # 4. Migrate in foreign-key dependency order
        models_in_order = [
            (StoreSetting, "store_settings"),
            (Customer, "customers"),
            (Product, "products"),
            (Sale, "sales"),
            (SaleItem, "sale_items"),
            (StockMovement, "stock_movements"),
            (GnaniApiUsage, "gnani_api_usage"),
        ]

        summary = {}
        for model_cls, table_name in models_in_order:
            cnt = migrate_table(sqlite_db, pg_db, model_cls, table_name)
            summary[table_name] = cnt

        # 5. Reset PostgreSQL auto-increment sequences
        table_names = [t for _, t in models_in_order]
        reset_postgres_sequences(pg_engine, table_names)

        # 6. Verification Audit
        logger.info("==========================================")
        logger.info("MIGRATION AUDIT SUMMARY:")
        logger.info("==========================================")
        with pg_engine.connect() as conn:
            for t in table_names:
                pg_cnt = conn.execute(text(f"SELECT COUNT(*) FROM {t};")).scalar()
                sqlite_cnt = summary.get(t, 0)
                status_str = "MATCH" if pg_cnt >= sqlite_cnt else "MISMATCH"
                logger.info(f"  {t:<18}: SQLite={sqlite_cnt:<5} | Postgres={pg_cnt:<5} [{status_str}]")
        logger.info("==========================================")
        logger.info("Migration completed successfully!")

    finally:
        sqlite_db.close()
        pg_db.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite to PostgreSQL for TamilVoice Kirana AI")
    parser.add_argument("--sqlite-path", default="kirana_ai.db", help="Path to SQLite database file")
    parser.add_argument("--postgres-url", default=os.getenv("DATABASE_URL", ""), help="Target PostgreSQL connection URL")
    parser.add_argument("--dry-run", action="store_true", help="Test connectivity without writing data")
    args = parser.parse_args()

    pg_url = args.postgres_url.strip()
    if not pg_url or not (pg_url.startswith("postgres://") or pg_url.startswith("postgresql://")):
        logger.error("Please supply a valid PostgreSQL connection URL via --postgres-url or DATABASE_URL env var.")
        logger.error("Example: python -m backend.app.migrate_sqlite_to_postgres --postgres-url 'postgresql://postgres:password@db.supabase.co:5432/postgres'")
        sys.exit(1)

    run_migration(args.sqlite_path, pg_url, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

