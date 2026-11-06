"""Sales Router: Transaction checkout and sales history."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas.sale import (
    SaleCreate,
    SaleResponse,
    SaleListResponse,
)
from backend.app.services import sales_service

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.post("", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
def record_sale(sale_in: SaleCreate, db: Session = Depends(get_db)):
    """
    Process and record a new retail sale transaction:
    - Atomically checks stock and deducts items
    - Computes prices and line totals from active DB records
    - Creates immutable snapshots of product name and unit price
    - Logs audit movement
    - Updates customer credit if Udhaar
    """
    sale = sales_service.create_sale(db=db, sale_in=sale_in)
    return sale


@router.get("", response_model=SaleListResponse)
def list_sales(
    start_date: Optional[datetime] = Query(None, description="Filter from start datetime"),
    end_date: Optional[datetime] = Query(None, description="Filter up to end datetime"),
    payment_method: Optional[str] = Query(None, description="CASH, UPI, CREDIT, CARD"),
    customer_id: Optional[int] = Query(None, description="Filter by customer ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Retrieve sales history with pagination and filters."""
    items, total, total_pages = sales_service.get_sales(
        db=db,
        start_date=start_date,
        end_date=end_date,
        payment_method=payment_method,
        customer_id=customer_id,
        page=page,
        limit=limit,
    )
    return SaleListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/{sale_id}", response_model=SaleResponse)
def get_sale(sale_id: int, db: Session = Depends(get_db)):
    """Retrieve details and receipt items for a specific sale transaction."""
    return sales_service.get_sale_by_id(db=db, sale_id=sale_id)


@router.get("/transaction/{transaction_id}", response_model=SaleResponse)
def get_sale_by_tx_id(transaction_id: str, db: Session = Depends(get_db)):
    """Retrieve sale by transaction code (e.g. TXN-20261106-ABCD)."""
    return sales_service.get_sale_by_transaction_id(db=db, transaction_id=transaction_id)
