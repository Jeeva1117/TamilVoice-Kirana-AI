"""Stock Adjustment & Movement Schemas."""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class StockAdjustmentType(str, Enum):
    ADD = "ADD"
    REMOVE = "REMOVE"
    SET = "SET"


class StockAdjustRequest(BaseModel):
    adjustment_type: StockAdjustmentType = Field(..., description="ADD, REMOVE, or SET")
    quantity: float = Field(..., ge=0.0, description="Quantity to add/remove or new total")
    reason: Optional[str] = Field("Manual inventory adjustment", max_length=255)
    reference_id: Optional[str] = Field(None, max_length=100)


class StockAdjustResponse(BaseModel):
    product_id: int
    sku: str
    product_name: str
    previous_quantity: float
    new_quantity: float
    change: float
    movement_type: str
    stock_status: str
    message: str


class StockMovementResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    movement_type: str
    quantity: float
    previous_quantity: float
    new_quantity: float
    reason: Optional[str] = None
    reference_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockMovementListResponse(BaseModel):
    items: List[StockMovementResponse]
    total: int

