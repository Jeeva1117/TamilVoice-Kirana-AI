"""Health Check Router."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.database import get_db
from backend.app.config import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", status_code=status.HTTP_200_OK)
def check_health(response: Response, db: Session = Depends(get_db)):
    """Health check endpoint that verifies API and database availability.
    
    Returns HTTP 200 with status='healthy' if database query succeeds.
    Returns HTTP 503 with status='unhealthy' if database query fails.
    """
    db_status = "connected"
    is_healthy = True
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
        is_healthy = False
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "database_type": "postgresql" if settings.is_postgres else "sqlite",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "timezone": settings.TIMEZONE,
    }

