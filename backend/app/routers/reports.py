"""Reports Router: Historical business reports and valuation."""
from datetime import date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas.reports import (
    DailyReportResponse,
    ProductPerformanceItem,
    InventoryValuationResponse,
)
from backend.app.services import reports_service
from backend.app.utils.helpers import get_ist_now

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/daily", response_model=DailyReportResponse)
def get_daily_sales_report(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Retrieve daily sales breakdown within date range."""
    if not end_date:
        end_date = get_ist_now().date()
    if not start_date:
        start_date = end_date - timedelta(days=6)  # Default last 7 days

    return reports_service.get_daily_report(db=db, start_date=start_date, end_date=end_date)


@router.get("/products", response_model=List[ProductPerformanceItem])
def get_product_sales_report(db: Session = Depends(get_db)):
    """Retrieve sales and performance metrics per product."""
    return reports_service.get_products_report(db=db)


@router.get("/inventory", response_model=InventoryValuationResponse)
def get_inventory_valuation_report(db: Session = Depends(get_db)):
    """Retrieve complete inventory valuation, cost vs retail, and margin projections."""
    return reports_service.get_inventory_valuation(db=db)
