"""Dashboard Router: Real-time Kirana metrics and charts."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas.dashboard import DashboardResponse
from backend.app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard_data(db: Session = Depends(get_db)):
    """
    Retrieve real-time dashboard analytics:
    - Today's revenue & order count (IST)
    - Low stock and out of stock product alerts
    - Total inventory value
    - Top selling products
    - Recent activities
    - Category sales breakdown
    - Hourly sales breakdown
    """
    return dashboard_service.get_dashboard_summary(db=db)
