"""
TamilVoice Kirana AI - Sales Router
Billing, invoice generation, and transaction records.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Sale, Product
from backend.schemas import SaleCreate, SaleResponse

router = APIRouter(prefix="/sales", tags=["Sales & Billing"])


@router.get("", response_model=List[SaleResponse])
def list_sales(
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Retrieve billing history and recent transactions."""
    query = db.query(Sale)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (Sale.invoice_number.ilike(search_fmt)) |
            (Sale.items_summary_en.ilike(search_fmt)) |
            (Sale.items_summary_ta.ilike(search_fmt))
        )
    return query.order_by(Sale.created_at.desc()).limit(limit).all()


@router.post("", response_model=SaleResponse, status_code=201)
def record_sale(sale_in: SaleCreate, db: Session = Depends(get_db)):
    """Record a counter sale and generate an invoice."""
    last_sale = db.query(Sale).order_by(Sale.id.desc()).first()
    next_num = 1090 if not last_sale else 1090 + last_sale.id
    invoice_num = f"KB-{next_num}"

    sale = Sale(
        invoice_number=invoice_num,
        items_summary_en=sale_in.items_summary_en,
        items_summary_ta=sale_in.items_summary_ta,
        total_amount=sale_in.total_amount,
        payment_method=sale_in.payment_method,
        status="completed",
        customer_id=sale_in.customer_id
    )
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale

