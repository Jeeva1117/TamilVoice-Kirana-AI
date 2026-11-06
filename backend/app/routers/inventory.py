"""Inventory Router: Product CRUD and search."""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
)
from backend.app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("", response_model=ProductListResponse)
def list_products(
    search: Optional[str] = Query(None, description="Search by name, Tamil name, or SKU"),
    category: Optional[str] = Query(None, description="Filter by category"),
    stock_status: Optional[str] = Query(None, description="in_stock, low_stock, out_of_stock"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    sort_by: str = Query("name", description="Field to sort by"),
    sort_order: str = Query("asc", description="Sort order: asc or desc"),
    db: Session = Depends(get_db)
):
    """Retrieve catalog products with comprehensive filtering and pagination."""
    items, total, total_pages = inventory_service.get_products(
        db=db,
        search=search,
        category=category,
        stock_status=stock_status,
        is_active=True,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/categories", response_model=List[str])
def list_categories(db: Session = Depends(get_db)):
    """Retrieve unique list of active product categories."""
    return inventory_service.get_categories(db)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product in the inventory catalog."""
    return inventory_service.create_product(db, product_in)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Retrieve a single product by its ID."""
    return inventory_service.get_product_by_id(db, product_id)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product_details(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db)
):
    """Update existing product details."""
    return inventory_service.update_product(db, product_id, product_in)


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
def remove_product(product_id: int, db: Session = Depends(get_db)):
    """Soft delete a product from active inventory."""
    inventory_service.delete_product(db, product_id)
    return {"success": True, "message": f"Product {product_id} deleted successfully."}

