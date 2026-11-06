"""Reports Service: Generates analytical reports for business performance."""
from datetime import date, datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models.sale import Sale
from backend.app.models.sale_item import SaleItem
from backend.app.models.product import Product
from backend.app.schemas.reports import (
    DailySalesSummary,
    DailyReportResponse,
    ProductPerformanceItem,
    InventoryValuationResponse,
)


def get_daily_report(db: Session, start_date: date, end_date: date) -> DailyReportResponse:
    """Daily revenue breakdown between start_date and end_date."""
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    sales = (
        db.query(
            func.date(Sale.created_at).label("sale_date"),
            func.sum(Sale.total_amount).label("day_revenue"),
            func.count(Sale.id).label("day_count")
        )
        .filter(
            Sale.created_at >= start_dt,
            Sale.created_at <= end_dt,
            Sale.status == "COMPLETED"
        )
        .group_by(func.date(Sale.created_at))
        .all()
    )

    breakdown = []
    total_rev = 0.0
    total_ord = 0

    sales_by_date = {row.sale_date: (float(row.day_revenue or 0.0), int(row.day_count or 0)) for row in sales}

    # Iterate through all days in range
    curr = start_date
    while curr <= end_date:
        d_str = curr.strftime("%Y-%m-%d")
        rev, cnt = sales_by_date.get(d_str, (0.0, 0))
        aov = round(rev / cnt, 2) if cnt > 0 else 0.0
        breakdown.append(
            DailySalesSummary(
                date=curr,
                total_sales=round(rev, 2),
                order_count=cnt,
                average_order_value=aov
            )
        )
        total_rev += rev
        total_ord += cnt
        curr += timedelta(days=1)

    return DailyReportResponse(
        start_date=start_date,
        end_date=end_date,
        total_revenue=round(total_rev, 2),
        total_orders=total_ord,
        daily_breakdown=breakdown
    )


def get_products_report(db: Session) -> List[ProductPerformanceItem]:
    """Performance report for each product."""
    products = db.query(Product).filter(Product.is_active == True).all()

    # Query units sold and revenue from sale items
    sales_data = (
        db.query(
            SaleItem.product_id,
            func.coalesce(func.sum(SaleItem.quantity), 0.0).label("total_units"),
            func.coalesce(func.sum(SaleItem.line_total), 0.0).label("total_rev")
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.status == "COMPLETED")
        .group_by(SaleItem.product_id)
        .all()
    )
    sales_map = {row.product_id: (float(row.total_units), float(row.total_rev)) for row in sales_data}

    result = []
    for p in products:
        units, rev = sales_map.get(p.id, (0.0, 0.0))
        result.append(
            ProductPerformanceItem(
                product_id=p.id,
                name=p.name,
                sku=p.sku,
                category=p.category,
                units_sold=round(units, 2),
                revenue=round(rev, 2),
                current_stock=p.quantity,
            )
        )

    # Sort by revenue descending
    result.sort(key=lambda x: x.revenue, reverse=True)
    return result


def get_inventory_valuation(db: Session) -> InventoryValuationResponse:
    """Calculate detailed inventory valuation and margin projections."""
    products = db.query(Product).filter(Product.is_active == True).all()

    total_cost = 0.0
    total_retail = 0.0
    total_qty = 0.0
    category_summary: Dict[str, Dict[str, float]] = {}

    for p in products:
        cost = p.quantity * p.purchase_price
        retail = p.quantity * p.selling_price
        total_cost += cost
        total_retail += retail
        total_qty += p.quantity

        cat = p.category or "General"
        if cat not in category_summary:
            category_summary[cat] = {"cost_value": 0.0, "retail_value": 0.0, "quantity": 0.0}
        category_summary[cat]["cost_value"] = round(category_summary[cat]["cost_value"] + cost, 2)
        category_summary[cat]["retail_value"] = round(category_summary[cat]["retail_value"] + retail, 2)
        category_summary[cat]["quantity"] = round(category_summary[cat]["quantity"] + p.quantity, 2)

    return InventoryValuationResponse(
        total_items=len(products),
        total_quantity=round(total_qty, 2),
        total_cost_value=round(total_cost, 2),
        total_retail_value=round(total_retail, 2),
        potential_profit=round(total_retail - total_cost, 2),
        category_summary=category_summary
    )
