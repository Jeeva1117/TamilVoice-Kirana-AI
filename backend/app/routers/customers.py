"""Customer Router: Manage store customers and credit/udhaar."""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.customer import Customer
from backend.app.models.sale import Sale
from backend.app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse,
    UdhaarPaymentRequest,
)
from backend.app.schemas.sale import SaleResponse

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=CustomerListResponse)
def list_customers(
    search: Optional[str] = Query(None, description="Search by customer name or phone"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Retrieve customers list with optional search."""
    query = db.query(Customer)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter((Customer.name.ilike(s)) | (Customer.phone.ilike(s)))

    total = query.count()
    offset = (page - 1) * limit
    items = query.order_by(Customer.name.asc()).offset(offset).limit(limit).all()
    return CustomerListResponse(items=items, total=total)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(cust_in: CustomerCreate, db: Session = Depends(get_db)):
    """Register a new regular customer."""
    customer = Customer(**cust_in.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Fetch customer details."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found."
        )
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    cust_in: CustomerUpdate,
    db: Session = Depends(get_db)
):
    """Update customer details or adjust balance."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found."
        )

    for field, val in cust_in.model_dump(exclude_unset=True).items():
        setattr(customer, field, val)

    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_200_OK)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """Delete a customer record."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found."
        )
    db.delete(customer)
    db.commit()
    return {"success": True, "message": f"Customer {customer_id} deleted."}


@router.post("/{customer_id}/payment")
def record_udhaar_payment(
    customer_id: int,
    payment_in: UdhaarPaymentRequest,
    db: Session = Depends(get_db)
):
    """
    Record an udhaar credit settlement payment from a customer.
    Deducts the paid amount from their outstanding credit balance.
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found."
        )

    initial_balance = customer.credit_balance
    new_balance = round(customer.credit_balance - payment_in.amount, 2)
    customer.credit_balance = new_balance
    db.commit()
    db.refresh(customer)

    return {
        "success": True,
        "customer_id": customer.id,
        "customer_name": customer.name,
        "amount_paid": payment_in.amount,
        "previous_balance": initial_balance,
        "remaining_balance": customer.credit_balance,
        "payment_method": payment_in.payment_method,
        "notes": payment_in.notes,
    }


@router.get("/{customer_id}/sales", response_model=List[SaleResponse])
def get_customer_sales(
    customer_id: int,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieve purchase history for a specific customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found."
        )

    sales = (
        db.query(Sale)
        .filter(Sale.customer_id == customer_id)
        .order_by(Sale.created_at.desc())
        .limit(limit)
        .all()
    )
    return sales


