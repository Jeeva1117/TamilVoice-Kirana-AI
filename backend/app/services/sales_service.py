"""Sales Service: Atomic transactions, stock deduction, pricing snapshots."""
import math
from typing import Optional, List, Tuple
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.models.sale import Sale
from backend.app.models.sale_item import SaleItem
from backend.app.models.product import Product
from backend.app.models.customer import Customer
from backend.app.models.stock_movement import StockMovement
from backend.app.schemas.sale import SaleCreate
from backend.app.utils.helpers import generate_transaction_id


def create_sale(db: Session, sale_in: SaleCreate) -> Sale:
    """
    Atomic transaction to record a sale:
    1. Validates products exist and have sufficient stock
    2. Server-computes prices and line totals (never trusts client totals)
    3. Deducts inventory atomically
    4. Logs StockMovement for each line item
    5. Records historical price and product name snapshots
    6. Updates customer credit balance if payment_method is CREDIT
    7. Rolls back completely on any error
    """
    if not sale_in.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sale must contain at least one product item."
        )

    # Optional customer check
    customer = None
    if sale_in.customer_id:
        customer = db.query(Customer).filter(Customer.id == sale_in.customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {sale_in.customer_id} not found."
            )

    txn_id = generate_transaction_id()

    try:
        # Create Sale shell
        sale = Sale(
            transaction_id=txn_id,
            customer_id=sale_in.customer_id,
            total_amount=0.0,
            payment_method=sale_in.payment_method.upper(),
            status="COMPLETED",
            notes=sale_in.notes
        )
        db.add(sale)
        db.flush()  # Populates sale.id for foreign key

        total_amount = 0.0

        for item in sale_in.items:
            # Query product with lock to avoid race conditions
            product = db.query(Product).filter(
                Product.id == item.product_id,
                Product.is_active == True
            ).with_for_update().first()

            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {item.product_id} not found or is inactive."
                )

            if item.quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Quantity for product '{product.name}' must be greater than zero."
                )

            # Stock check
            if product.quantity < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Insufficient stock for '{product.name}'. "
                        f"Available: {product.quantity} {product.unit}, Requested: {item.quantity} {product.unit}."
                    )
                )

            # Deduct inventory
            prev_qty = product.quantity
            new_qty = round(prev_qty - item.quantity, 3)
            product.quantity = new_qty

            # Calculate server-side total
            unit_price = round(product.selling_price, 2)
            line_total = round(item.quantity * unit_price, 2)
            total_amount += line_total

            # Create SaleItem with historical price snapshot
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                product_name_snapshot=product.name,
                quantity=item.quantity,
                unit=product.unit,
                unit_price=unit_price,
                line_total=line_total,
            )
            db.add(sale_item)

            # Audit stock movement
            movement = StockMovement(
                product_id=product.id,
                movement_type="SALE",
                quantity=item.quantity,
                previous_quantity=prev_qty,
                new_quantity=new_qty,
                reason=f"Sale {txn_id}",
                reference_id=txn_id,
            )
            db.add(movement)

        # Finalize total
        sale.total_amount = round(total_amount, 2)

        # Handle Udhaar / Credit
        if sale_in.payment_method.upper() == "CREDIT" and customer:
            customer.credit_balance = round(customer.credit_balance + total_amount, 2)

        db.commit()
        db.refresh(sale)
        return sale

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process sale transaction: {str(e)}"
        )


def get_sales(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    payment_method: Optional[str] = None,
    customer_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20,
) -> Tuple[List[Sale], int, int]:
    """Retrieve paginated sales list with filters."""
    query = db.query(Sale)

    if start_date:
        query = query.filter(Sale.created_at >= start_date)
    if end_date:
        query = query.filter(Sale.created_at <= end_date)
    if payment_method and payment_method != "ALL":
        query = query.filter(Sale.payment_method == payment_method.upper())
    if customer_id:
        query = query.filter(Sale.customer_id == customer_id)

    total = query.count()
    total_pages = math.ceil(total / limit) if limit > 0 else 1
    offset = (page - 1) * limit
    items = query.order_by(desc(Sale.created_at)).offset(offset).limit(limit).all()

    return items, total, total_pages


def get_sale_by_id(db: Session, sale_id: int) -> Sale:
    """Retrieve single sale by primary key ID."""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sale with ID {sale_id} not found."
        )
    return sale


def get_sale_by_transaction_id(db: Session, transaction_id: str) -> Sale:
    """Retrieve sale by transaction ID string."""
    sale = db.query(Sale).filter(Sale.transaction_id == transaction_id.strip()).first()
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{transaction_id}' not found."
        )
    return sale
