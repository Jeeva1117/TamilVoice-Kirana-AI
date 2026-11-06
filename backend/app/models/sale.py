"""Sale Database Model."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(50), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    total_amount = Column(Float, nullable=False, default=0.0)
    payment_method = Column(String(30), nullable=False, default="CASH")  # CASH, UPI, CREDIT, CARD
    status = Column(String(30), nullable=False, default="COMPLETED")  # COMPLETED, CANCELLED, REFUNDED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    customer = relationship("Customer", back_populates="sales")
    items = relationship(
        "SaleItem",
        back_populates="sale",
        cascade="all, delete-orphan",
        order_by="SaleItem.id"
    )
