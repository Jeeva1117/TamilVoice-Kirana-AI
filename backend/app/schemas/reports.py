"""Analytics and Reporting Schemas."""
from datetime import date
from typing import List, Dict
from pydantic import BaseModel


class DailySalesSummary(BaseModel):
    date: date
    total_sales: float
    order_count: int
    average_order_value: float


class DailyReportResponse(BaseModel):
    start_date: date
    end_date: date
    total_revenue: float
    total_orders: int
    daily_breakdown: List[DailySalesSummary]


class CategoryPerformance(BaseModel):
    category: str
    units_sold: float
    revenue: float
    percentage: float


class ProductPerformanceItem(BaseModel):
    product_id: int
    name: str
    sku: str
    category: str
    units_sold: float
    revenue: float
    current_stock: float


 class InventoryValuationResponse(BaseModel):
    total_items: int
    total_quantity: float
    total_cost_value: float
    total_retail_value: float
    potential_profit: float
    category_summary: Dict[str, Dict[str, float]]
