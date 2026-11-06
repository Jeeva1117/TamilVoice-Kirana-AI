"""Inventory Service: Business logic for products and catalog."""
import math
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc
from backend.app.models.product import Product
from backend.app.models.stock_movement import StockMovement
from backend.app.schemas.product import ProductCreate, ProductUpdate


def get_products(
    db: Session,
    search: Optional[str] = None,
    category: Optional[str] = None,
    stock_status: Optional[str] = None,
    is_active: bool = True,
    page: int = 1,
    limit: int = 50,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> Tuple[List[Product], int, int]:
    """Retrieve filtered, paginated list of products."""
    query = db.query(Product).filter(Product.is_active == is_active)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Product.name.ilike(search_term),
                Product.name_ta.ilike(search_term),
                Product.sku.ilike(search_term),
                Product.category.ilike(search_term),
            )
        )

    if category and category != "all":
        query = query.filter(Product.category.ilike(category.strip()))

    if stock_status:
        stock_status = stock_status.lower()
        if stock_status == "out_of_stock":
            query = query.filter(Product.quantity <= 0)
        elif stock_status == "low_stock":
            query = query.filter(
                Product.quantity > 0,
                Product.quantity <= Product.minimum_stock_level
            )
        elif stock_status == "in_stock":
            query = query.filter(Product.quantity > Product.minimum_stock_level)

    # Sorting
    sort_col = getattr(Product, sort_by, Product.name)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_col))
    else:
        query = query.order_by(asc(sort_col))

    total = query.count()
    total_pages = math.ceil(total / limit) if limit > 0 else 1
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()

    return items, total, total_pages


def get_product_by_id(db: Session, product_id: int) -> Product:
    """Fetch product by ID or raise 404."""
    product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found."
        )
    return product


def get_product_by_sku(db: Session, sku: str) -> Optional[Product]:
    """Fetch product by SKU."""
    return db.query(Product).filter(Product.sku.ilike(sku.strip()), Product.is_active == True).first()


def create_product(db: Session, product_in: ProductCreate) -> Product:
    """Create new product with SKU uniqueness validation."""
    existing = db.query(Product).filter(Product.sku.ilike(product_in.sku.strip())).first()
    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with SKU '{product_in.sku}' already exists."
            )
        else:
            # Reactivate soft-deleted product
            for field, value in product_in.model_dump().items():
                setattr(existing, field, value)
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            return existing

    product = Product(**product_in.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)

    # Log initial stock movement if quantity > 0
    if product.quantity > 0:
        movement = StockMovement(
            product_id=product.id,
            movement_type="PURCHASE",
            quantity=product.quantity,
            previous_quantity=0.0,
            new_quantity=product.quantity,
            reason="Initial inventory creation",
            reference_id=f"INIT-{product.sku}"
        )
        db.add(movement)
        db.commit()

    return product


def update_product(db: Session, product_id: int, product_in: ProductUpdate) -> Product:
    """Update existing product details."""
    product = get_product_by_id(db, product_id)

    update_data = product_in.model_dump(exclude_unset=True)

    # If SKU is updated, ensure uniqueness
    if "sku" in update_data and update_data["sku"] != product.sku:
        existing = db.query(Product).filter(
            Product.sku.ilike(update_data["sku"].strip()),
            Product.id != product_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SKU '{update_data['sku']}' is already in use by another product."
            )

    # Check if quantity directly changed via update
    if "quantity" in update_data and update_data["quantity"] != product.quantity:
        prev_qty = product.quantity
        new_qty = update_data["quantity"]
        diff = new_qty - prev_qty
        m_type = "ADJUSTMENT_ADD" if diff > 0 else "ADJUSTMENT_REMOVE"
        movement = StockMovement(
            product_id=product.id,
            movement_type=m_type,
            quantity=abs(diff),
            previous_quantity=prev_qty,
            new_quantity=new_qty,
            reason="Direct product update",
            reference_id=f"UPD-{product.sku}"
        )
        db.add(movement)

    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> bool:
    """Soft delete product (preserves historical receipts and audit logs)."""
    product = get_product_by_id(db, product_id)
    product.is_active = False
    db.commit()
    return True


def get_categories(db: Session) -> List[str]:
    """Retrieve distinct product categories."""
    categories = (
        db.query(Product.category)
        .filter(Product.is_active == True)
        .distinct()
        .order_by(Product.category)
        .all()
    )
    return [c[0] for c in categories if c[0]]

