"""Reports Router: Historical business reports and valuation."""
import io
import csv
from datetime import date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Response, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas.reports import (
    DailyReportResponse,
    ProductPerformanceItem,
    InventoryValuationResponse,
)
from backend.app.models.product import Product
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


@router.get("/export/csv")
def export_report_csv(
    report_type: str = Query("products", description="Report category: 'products', 'daily', or 'inventory'"),
    start_date: Optional[date] = Query(None, description="Start date for daily report"),
    end_date: Optional[date] = Query(None, description="End date for daily report"),
    db: Session = Depends(get_db)
):
    """
    Generate downloadable CSV spreadsheet for Kirana store accounts & taxation.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    today_str = get_ist_now().strftime("%Y%m%d")

    if report_type == "products":
        writer.writerow(["Product ID", "SKU", "Product Name", "Category", "Units Sold", "Total Revenue (INR)", "Current Stock"])
        items = reports_service.get_products_report(db)
        for item in items:
            writer.writerow([
                item.product_id,
                item.sku,
                item.name,
                item.category or "General",
                item.units_sold,
                item.revenue,
                item.current_stock,
            ])
        filename = f"kirana_products_report_{today_str}.csv"

    elif report_type == "daily":
        if not end_date:
            end_date = get_ist_now().date()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        writer.writerow(["Date", "Total Revenue (INR)", "Orders Count", "Average Order Value (INR)"])
        report = reports_service.get_daily_report(db, start_date=start_date, end_date=end_date)
        for row in report.daily_breakdown:
            writer.writerow([
                row.date.strftime("%Y-%m-%d"),
                row.total_sales,
                row.order_count,
                row.average_order_value,
            ])
        filename = f"kirana_daily_sales_{today_str}.csv"

    elif report_type == "inventory":
        writer.writerow(["Product ID", "SKU", "Name", "Category", "Stock Qty", "Unit", "Cost Price (INR)", "Selling Price (INR)", "Total Cost (INR)", "Retail Value (INR)"])
        products = db.query(Product).filter(Product.is_active == True).order_by(Product.name.asc()).all()
        for p in products:
            cost_val = round(p.quantity * p.purchase_price, 2)
            retail_val = round(p.quantity * p.selling_price, 2)
            writer.writerow([
                p.id,
                p.sku,
                p.name,
                p.category or "General",
                p.quantity,
                p.unit,
                p.purchase_price,
                p.selling_price,
                cost_val,
                retail_val,
            ])
        filename = f"kirana_inventory_valuation_{today_str}.csv"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown report type '{report_type}'. Must be 'products', 'daily', or 'inventory'."
        )

    csv_data = output.getvalue()
    output.close()

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache",
        }
    )


