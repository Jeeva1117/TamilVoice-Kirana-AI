"""Stock Service: Manages stock adjustments and audit history."""
from typing import List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models.product import Product
from backend.app.models.stock_movement import StockMovement
from backend.app.schemas.stock import StockAdjustmentType, StockAdjustResponse


def adjust_stock(
    db: Session,
    product_id: int,
    adjustment_type: StockAdjustmentType,
    quantity: float,
    reason: str = "Manual inventory adjustment",
    reference_id: str = None
) -> StockAdjustResponse:
    """Perform atomic stock adjustment with validation and audit logging."""
    if quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity cannot be negative."
        )

    try:
        product = db.query(Product).filter(
            Product.id == product_id,
            Product.is_active == True
        ).with_for_update().first()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found."
            )

        prev_qty = product.quantity
        adj_type_str = str(adjustment_type).upper()

        if adj_type_str == StockAdjustmentType.ADD.value:
            if quantity == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quantity to add must be greater than zero."
                )
            new_qty = prev_qty + quantity
            movement_type = "ADJUSTMENT_ADD"
            change = quantity

        elif adj_type_str == StockAdjustmentType.REMOVE.value:
            if quantity == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quantity to remove must be greater than zero."
                )
            if prev_qty < quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Insufficient stock for '{product.name}'. "
                        f"Current: {prev_qty} {product.unit}, Requested deduction: {quantity} {product.unit}."
                    )
                )
            new_qty = prev_qty - quantity
            movement_type = "ADJUSTMENT_REMOVE"
            change = -quantity

        elif adj_type_str == StockAdjustmentType.SET.value:
            new_qty = quantity
            movement_type = "SET_STOCK"
            change = new_qty - prev_qty

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid adjustment type: {adjustment_type}"
            )

        # Update product stock
        product.quantity = round(new_qty, 3)

        # Create movement log
        movement = StockMovement(
            product_id=product.id,
            movement_type=movement_type,
            quantity=round(abs(change), 3),
            previous_quantity=round(prev_qty, 3),
            new_quantity=round(new_qty, 3),
            reason=reason or "Stock level adjustment",
            reference_id=reference_id
        )
        db.add(movement)
        db.commit()
        db.refresh(product)

        msg = f"Stock updated: {prev_qty} -> {new_qty} {product.unit} ({movement_type})"
        return StockAdjustResponse(
            product_id=product.id,
            sku=product.sku,
            product_name=product.name,
            previous_quantity=prev_qty,
            new_quantity=new_qty,
            change=change,
            movement_type=movement_type,
            stock_status=product.stock_status,
            message=msg
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adjusting stock: {str(e)}"
        )


def get_product_movements(db: Session, product_id: int, limit: int = 50) -> List[StockMovement]:
    """Retrieve audit history of stock movements for a specific product."""
    return (
        db.query(StockMovement)
        .filter(StockMovement.product_id == product_id)
        .order_by(StockMovement.created_at.desc())
        .limit(limit)
        .all()
    )


def get_all_movements(db: Session, limit: int = 50) -> List[StockMovement]:
    """Retrieve recent stock movements across all products."""
    return (
        db.query(StockMovement)
        .order_by(StockMovement.created_at.desc())
        .limit(limit)
        .all()
    )
