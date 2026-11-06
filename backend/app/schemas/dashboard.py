"""Dashboard Pydantic Schemas."""
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel


class DashboardKPIs(BaseModel):
    today_sales: float
    today_sales_change_pct: float
    today_orders: int
    low_stock_count: int
    out_of_stock_count: int
    total_products: int
    total_inventory_value: float


class TopProductItem(BaseModel):
    product_id: int
    name: str
    name_ta: Optional[str] = None
    units_sold: float
    revenue: float


class RecentActivityItem(BaseModel):
    id: str
    type: str  # "sale", "stock_adjustment", "product_created"
    description: str
    amount: Optional[float] = None
    timestamp: datetime


class HourlySalesPoint(BaseModel):
    hour: str
    amount: float


class DashboardResponse(BaseModel):
    kpis: DashboardKPIs
    top_products: List[TopProductItem]
    recent_activities: List[RecentActivityItem]
    sales_by_category: Dict[str, float]
    hourly_sales: List[HourlySalesPoint]
