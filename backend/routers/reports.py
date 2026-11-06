"""
TamilVoice Kirana AI - Reports & Analytics Router
Endpoints for daily, weekly, and monthly business summaries.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.database import get_db

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


@router.get("/daily")
def get_daily_report(date: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Daily revenue, order volume, and category distribution."""
    return {
        "period": "daily",
        "date": date or "Today",
        "total_revenue": 18450.0,
        "completed_bills": 142,
        "average_basket_size": 130.0,
        "top_category": "Rice & Grains",
        "cash_sales": 12200.0,
        "upi_sales": 5150.0,
        "credit_khata_sales": 1100.0
    }


@router.get("/weekly")
def get_weekly_report(start_date: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Weekly sales trend and top products."""
    return {
        "period": "weekly",
        "total_revenue": 130500.0,
        "total_orders": 881,
        "growth_rate": "+8.4%",
        "daily_breakdown": [
            {"day": "Mon", "revenue": 14200},
            {"day": "Tue", "revenue": 16800},
            {"day": "Wed", "revenue": 15300},
            {"day": "Thu", "revenue": 17900},
            {"day": "Fri", "revenue": 19400},
            {"day": "Sat", "revenue": 24800},
            {"day": "Sun", "revenue": 22100}
        ]
    }


@router.get("/monthly")
def get_monthly_report(year: Optional[int] = 2026, month: Optional[int] = 11, db: Session = Depends(get_db)):
    """Monthly revenue and inventory movement summary."""
    return {
        "period": "monthly",
        "year": year,
        "month": month,
        "total_revenue": 442500.0,
        "total_orders": 3260,
        "estimated_gross_profit": 57500.0
    }
