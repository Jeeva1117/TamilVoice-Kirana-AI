"""
TamilVoice Kirana AI - Database Configuration
SQLite engine using SQLAlchemy ORM.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database URL - SQLite local file
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tamilvoice_kirana.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

