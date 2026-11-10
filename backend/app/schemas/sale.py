"""Sale and Sale Items Schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class SaleItemCreate(BaseModel):
    product_id: int = Field(..., gt=0, description="Product ID to purchase")
    quantity: float = Field(..., gt=0, description="Quantity to purchase (must be > 0)")


class SaleCreate(BaseModel):
    items: List[SaleItemCreate] = Field(..., min_length=1, description="List of items in sale")
    payment_method: str = Field("CASH", description="CASH, UPI, CREDIT, CARD")
    customer_id: Optional[int] = Field(None, description="Optional customer ID")
    notes: Optional[str] = Field(None, max_length=500, description="Optional transaction notes")
    idempotency_key: Optional[str] = Field(None, max_length=100, description="Optional unique idempotency key to prevent duplicate checkouts")


class SaleItemResponse(BaseModel):
    id: int
    sale_id: int
    product_id: Optional[int]
    product_name_snapshot: str
    quantity: float
    unit: str
    unit_price: float
    line_total: float

    model_config = ConfigDict(from_attributes=True)


class SaleResponse(BaseModel):
    id: int
    transaction_id: str
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    total_amount: float
    payment_method: str
    status: str
    notes: Optional[str] = None
    created_at: datetime
    items: List[SaleItemResponse]

    model_config = ConfigDict(from_attributes=True)


class SaleListResponse(BaseModel):
    items: List[SaleResponse]
    total: int
    page: int
    limit: int
    total_pages: int

