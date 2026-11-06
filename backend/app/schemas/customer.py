"""Customer Pydantic Schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None)
    credit_balance: float = Field(0.0, description="Outstanding udhaar / credit balance")


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    credit_balance: Optional[float] = None


class CustomerResponse(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerListResponse(BaseModel):
    items: List[CustomerResponse]
    total: int
