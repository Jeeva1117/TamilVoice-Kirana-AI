"""Stock Router: Stock adjustments and movement logs."""
from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas.stock import (
    StockAdjustRequest,
    StockAdjustResponse,
    StockMovementResponse,
)
from backend.app.services import stock_service

router = APIRouter(prefix="/inventory", tags=["Stock Management"])


@router.post("/{product_id}/adjust", response_model=StockAdjustResponse, status_code=status.HTTP_200_OK)
def adjust_inventory_level(
    product_id: int,
    adj_in: StockAdjustRequest,
    db: Session = Depends(get_db)
):
    """
    Perform an atomic stock adjustment (ADD, REMOVE, or SET).
    Prevents negative inventory and writes an audit log.
    """
    return stock_service.adjust_stock(
        db=db,
        product_id=product_id,
        adjustment_type=adj_in.adjustment_type,
        quantity=adj_in.quantity,
        reason=adj_in.reason,
        reference_id=adj_in.reference_id,
    )


@router.get("/{product_id}/movements", response_model=List[StockMovementResponse])
def get_product_movement_history(
    product_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Retrieve audit history of stock adjustments and sales for a specific product."""
    return stock_service.get_product_movements(db=db, product_id=product_id, limit=limit)


@router.get("/movements/all", response_model=List[StockMovementResponse])
def get_all_movements_history(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Retrieve all recent inventory movements across all products."""
    return stock_service.get_all_movements(db=db, limit=limit)
