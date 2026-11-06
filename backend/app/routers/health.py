"""Health Check Router."""
from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.database import get_db
from backend.app.config import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", status_code=status.HTTP_200_OK)
def check_health(db: Session = Depends(get_db)):
    """Health check endpoint that verifies API and SQLite database availability."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "timezone": settings.TIMEZONE,
    }
