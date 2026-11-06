"""Product Database Model."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    name_ta = Column(String(255), nullable=True)
    sku = Column(String(50), unique=True, index=True, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    quantity = Column(Float, nullable=False, default=0.0)
    unit = Column(String(30), nullable=False, default="kg")
    purchase_price = Column(Float, nullable=False, default=0.0)
    selling_price = Column(Float, nullable=False, default=0.0)
    minimum_stock_level = Column(Float, nullable=False, default=10.0)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    stock_movements = relationship(
        "StockMovement",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="desc(StockMovement.created_at)"
    )
    sale_items = relationship(
        "SaleItem",
        back_populates="product"
    )

    @property
    def is_low_stock(self) -> bool:
        return 0 < self.quantity <= self.minimum_stock_level

    @property
    def is_out_of_stock(self) -> bool:
        return self.quantity <= 0

    @property
    def stock_status(self) -> str:
        if self.quantity <= 0:
            return "out_of_stock"
        elif self.quantity <= self.minimum_stock_level:
            return "low_stock"
        return "in_stock"
