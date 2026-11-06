"""
TamilVoice Kirana AI - Pydantic Schemas
Data contracts for validation and response serialization.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ==========================================
# Product / Inventory Schemas
# ==========================================
class ProductBase(BaseModel):
    name_en: str = Field(..., example="Ponni Boiled Rice 25kg")
    name_ta: str = Field(..., example="பொன்னி புழுங்கல் அரிசி 25kg")
    category: str = Field("Grocery", example="Rice")
    stock: float = Field(0.0, ge=0)
    min_stock: float = Field(5.0, ge=0)
    unit: str = Field("kg", example="bags")
    purchase_price: float = Field(0.0, ge=0)
    selling_price: float = Field(0.0, ge=0)


class ProductCreate(ProductBase):
    sku: Optional[str] = None


class ProductUpdate(BaseModel):
    name_en: Optional[str] = None
    name_ta: Optional[str] = None
    category: Optional[str] = None
    stock: Optional[float] = None
    min_stock: Optional[float] = None
    unit: Optional[str] = None
    purchase_price: Optional[float] = None
    selling_price: Optional[float] = None


class ProductResponse(ProductBase):
    id: int
    sku: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# Sale / Order Schemas
# ==========================================
class SaleCreate(BaseModel):
    items_summary_en: str
    items_summary_ta: str
    total_amount: float = Field(..., ge=0)
    payment_method: str = "Cash"
    customer_id: Optional[int] = None


class SaleResponse(BaseModel):
    id: int
    invoice_number: str
    items_summary_en: str
    items_summary_ta: str
    total_amount: float
    payment_method: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# Dashboard Schemas
# ==========================================
class DashboardKPIs(BaseModel):
    todayRevenue: float
    revenueChange: str
    totalSales: int
    salesChange: str
    ordersToday: int
    ordersChange: str
    lowStockCount: int
    totalProducts: int


class DashboardResponse(BaseModel):
    kpis: DashboardKPIs
    analytics: Dict[str, Any]
    lowStock: List[Dict[str, Any]]
    recentTransactions: List[Dict[str, Any]]
    topProducts: List[Dict[str, Any]]


# ==========================================
# Voice Processing Schemas
# ==========================================
class VoiceProcessRequest(BaseModel):
    transcript: Optional[str] = None
    language: str = "ta"


class VoiceProcessResponse(BaseModel):
    transcript: str
    action: str
    action_ta: str
    product: Optional[str] = None
    product_ta: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    confidence: float
    requires_confirmation: bool
    response_ta: str
    response_tanglish: str
    response_en: str

