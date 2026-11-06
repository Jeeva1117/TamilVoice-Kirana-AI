"""
TamilVoice Kirana AI - Database Models
SQLAlchemy ORM models for inventory products, sales transactions, and customer khata.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from backend.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, index=True, nullable=True)
    name_en = Column(String(200), nullable=False, index=True)
    name_ta = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False, default="Grocery", index=True)
    stock = Column(Float, nullable=False, default=0.0)
    min_stock = Column(Float, nullable=False, default=5.0)
    unit = Column(String(50), nullable=False, default="kg")
    purchase_price = Column(Float, nullable=False, default=0.0)
    selling_price = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def status(self) -> str:
        if self.stock <= 0:
            return "out_of_stock"
        elif self.stock <= self.min_stock / 2:
            return "critical"
        elif self.stock <= self.min_stock:
            return "warning"
        return "in_stock"


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), unique=True, index=True, nullable=False)
    items_summary_en = Column(Text, nullable=False)
    items_summary_ta = Column(Text, nullable=False)
    total_amount = Column(Float, nullable=False, default=0.0)
    payment_method = Column(String(50), nullable=False, default="Cash")  # Cash, UPI, Credit
    status = Column(String(50), nullable=False, default="completed")
    customer_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    credit_balance = Column(Float, nullable=False, default=0.0)  # Udhaar Khata
    created_at = Column(DateTime, default=datetime.utcnow)
