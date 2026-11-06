"""
TamilVoice Kirana AI - Inventory Router
CRUD operations and stock adjustments for Kirana store inventory.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Product
from backend.schemas import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("", response_model=List[ProductResponse])
def list_inventory(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name"),
    status: Optional[str] = Query(None, description="Filter by stock status"),
    db: Session = Depends(get_db)
):
    """Retrieve all inventory products with filtering and search."""
    query = db.query(Product)

    if category and category.lower() != "all":
        query = query.filter(Product.category.ilike(f"%{category}%"))

    if search:
        search_fmt = f"%{search}%"
        query = query.filter((Product.name_en.ilike(search_fmt)) | (Product.name_ta.ilike(search_fmt)))

    products = query.order_by(Product.id.asc()).all()

    if status:
        products = [p for p in products if p.status == status]

    return products


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    """Add a new product to store inventory."""
    product = Product(
        sku=product_in.sku or f"SKU-{product_in.category[:3].upper()}-{db.query(Product).count() + 1:03d}",
        name_en=product_in.name_en,
        name_ta=product_in.name_ta,
        category=product_in.category,
        stock=product_in.stock,
        min_stock=product_in.min_stock,
        unit=product_in.unit,
        purchase_price=product_in.purchase_price,
        selling_price=product_in.selling_price
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_in: ProductUpdate, db: Session = Depends(get_db)):
    """Update existing product details or pricing."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Remove a product from inventory."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()
    return {"message": f"Product '{product.name_en}' deleted successfully"}

