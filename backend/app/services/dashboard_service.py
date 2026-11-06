"""Dashboard Service: Real-time business KPI aggregation in IST timezone."""
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from backend.app.models.sale import Sale
from backend.app.models.sale_item import SaleItem
from backend.app.models.product import Product
from backend.app.models.stock_movement import StockMovement
from backend.app.schemas.dashboard import (
    DashboardKPIs,
    TopProductItem,
    RecentActivityItem,
    HourlySalesPoint,
    DashboardResponse,
)
from backend.app.utils.helpers import get_ist_now, get_ist_day_bounds


def get_dashboard_summary(db: Session) -> DashboardResponse:
    """Compute live dashboard metrics."""
    now_ist = get_ist_now()
    today_date = now_ist.date()
    yesterday_date = today_date - timedelta(days=1)

    today_start_utc, today_end_utc = get_ist_day_bounds(today_date)
    yest_start_utc, yest_end_utc = get_ist_day_bounds(yesterday_date)

    # 1. Today's sales & orders
    today_sales_agg = (
        db.query(
            func.coalesce(func.sum(Sale.total_amount), 0.0),
            func.count(Sale.id)
        )
        .filter(
            Sale.created_at >= today_start_utc,
            Sale.created_at <= today_end_utc,
            Sale.status == "COMPLETED"
        )
        .first()
    )
    today_sales = float(today_sales_agg[0] or 0.0)
    today_orders = int(today_sales_agg[1] or 0)

    # 2. Yesterday's sales
    yest_sales_agg = (
        db.query(func.coalesce(func.sum(Sale.total_amount), 0.0))
        .filter(
            Sale.created_at >= yest_start_utc,
            Sale.created_at <= yest_end_utc,
            Sale.status == "COMPLETED"
        )
        .scalar()
    )
    yest_sales = float(yest_sales_agg or 0.0)

    # Growth percentage
    if yest_sales > 0:
        change_pct = round(((today_sales - yest_sales) / yest_sales) * 100, 1)
    else:
        change_pct = 100.0 if today_sales > 0 else 0.0

    # 3. Product & inventory metrics
    active_products = db.query(Product).filter(Product.is_active == True).all()
    total_products = len(active_products)
    low_stock_count = sum(1 for p in active_products if 0 < p.quantity <= p.minimum_stock_level)
    out_of_stock_count = sum(1 for p in active_products if p.quantity <= 0)
    total_inventory_value = round(sum(p.quantity * p.purchase_price for p in active_products), 2)

    kpis = DashboardKPIs(
        today_sales=round(today_sales, 2),
        today_sales_change_pct=change_pct,
        today_orders=today_orders,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        total_products=total_products,
        total_inventory_value=total_inventory_value,
    )

    # 4. Top Selling Products
    top_items_query = (
        db.query(
            SaleItem.product_id,
            SaleItem.product_name_snapshot,
            func.sum(SaleItem.quantity).label("units_sold"),
            func.sum(SaleItem.line_total).label("revenue")
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.status == "COMPLETED")
        .group_by(SaleItem.product_id, SaleItem.product_name_snapshot)
        .order_by(desc("units_sold"))
        .limit(5)
        .all()
    )

    top_products = []
    for row in top_items_query:
        # Check Tamil name if available
        p = db.query(Product).filter(Product.id == row.product_id).first() if row.product_id else None
        top_products.append(
            TopProductItem(
                product_id=row.product_id or 0,
                name=row.product_name_snapshot,
                name_ta=p.name_ta if p else None,
                units_sold=round(float(row.units_sold), 2),
                revenue=round(float(row.revenue), 2),
            )
        )

    # 5. Recent Activity
    recent_activities: List[RecentActivityItem] = []

    # Recent sales
    recent_sales = db.query(Sale).order_by(Sale.created_at.desc()).limit(5).all()
    for s in recent_sales:
        recent_activities.append(
            RecentActivityItem(
                id=f"sale-{s.id}",
                type="sale",
                description=f"Sale {s.transaction_id} ({s.payment_method})",
                amount=s.total_amount,
                timestamp=s.created_at,
            )
        )

    # Recent stock adjustments
    recent_moves = (
        db.query(StockMovement, Product.name)
        .join(Product, Product.id == StockMovement.product_id)
        .filter(StockMovement.movement_type != "SALE")
        .order_by(StockMovement.created_at.desc())
        .limit(5)
        .all()
    )
    for move, prod_name in recent_moves:
        recent_activities.append(
            RecentActivityItem(
                id=f"stock-{move.id}",
                type="stock_adjustment",
                description=f"{prod_name}: {move.movement_type} ({move.quantity}) - {move.reason or 'Adjusted'}",
                amount=None,
                timestamp=move.created_at,
            )
        )

    # Sort merged activities
    recent_activities.sort(key=lambda a: a.timestamp, reverse=True)
    recent_activities = recent_activities[:8]

    # 6. Sales by Category
    category_sales_query = (
        db.query(
            Product.category,
            func.sum(SaleItem.line_total).label("cat_revenue")
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.status == "COMPLETED")
        .group_by(Product.category)
        .all()
    )
    sales_by_category: Dict[str, float] = {
        row[0]: round(float(row[1]), 2) for row in category_sales_query if row[0]
    }

    # 7. Hourly Sales for today (8 AM to 9 PM)
    hours = [f"{h:02d}:00" for h in range(8, 22)]
    hourly_dict = {h: 0.0 for h in hours}
    today_sales_list = (
        db.query(Sale)
        .filter(
            Sale.created_at >= today_start_utc,
            Sale.created_at <= today_end_utc,
            Sale.status == "COMPLETED"
        )
        .all()
    )
    for sale in today_sales_list:
        sale_hour = sale.created_at.strftime("%H:00")
        if sale_hour in hourly_dict:
            hourly_dict[sale_hour] += sale.total_amount

    hourly_sales = [HourlySalesPoint(hour=h, amount=round(amt, 2)) for h, amt in hourly_dict.items()]

    return DashboardResponse(
        kpis=kpis,
        top_products=top_products,
        recent_activities=recent_activities,
        sales_by_category=sales_by_category,
        hourly_sales=hourly_sales,
    )
