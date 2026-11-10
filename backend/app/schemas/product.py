"""Product Pydantic Schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Product name in English")
    name_ta: Optional[str] = Field(None, max_length=255, description="Product name in Tamil")
    sku: str = Field(..., min_length=2, max_length=50, description="Unique Stock Keeping Unit")
    category: str = Field(..., min_length=1, max_length=100, description="Product category")
    quantity: float = Field(0.0, ge=0.0, description="Available stock quantity")
    unit: str = Field("kg", min_length=1, max_length=30, description="Measurement unit (kg, litre, pcs, etc.)")
    purchase_price: float = Field(0.0, ge=0.0, description="Cost price per unit")
    selling_price: float = Field(..., gt=0.0, description="Selling price per unit")
    minimum_stock_level: float = Field(10.0, ge=0.0, description="Threshold for low stock alert")
    reorder_level: Optional[float] = Field(15.0, ge=0.0, description="Suggested reorder threshold")
    aliases: Optional[str] = Field(None, description="Comma-separated aliases or multilingual keywords")
    description: Optional[str] = Field(None, description="Optional product description")
    is_active: bool = Field(True, description="Active status for soft delete")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    name_ta: Optional[str] = Field(None, max_length=255)
    sku: Optional[str] = Field(None, min_length=2, max_length=50)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    quantity: Optional[float] = Field(None, ge=0.0)
    unit: Optional[str] = Field(None, min_length=1, max_length=30)
    purchase_price: Optional[float] = Field(None, ge=0.0)
    selling_price: Optional[float] = Field(None, gt=0.0)
    minimum_stock_level: Optional[float] = Field(None, ge=0.0)
    reorder_level: Optional[float] = Field(None, ge=0.0)
    aliases: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    id: int
    is_low_stock: bool
    is_out_of_stock: bool
    stock_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    limit: int
    total_pages: int

