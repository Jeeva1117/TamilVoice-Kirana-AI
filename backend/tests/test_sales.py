"""Test suite for sales transactions, atomic guarantees, and historical snapshots."""
from fastapi import status
from backend.app.models.product import Product


def test_record_sale_success(client, db, sample_product):
    """Test recording a valid sale with server-side price computation and stock deduction."""
    # Add a second product
    prod2 = Product(
        name="Gold Winner Sunflower Oil 1L",
        sku="TEST-OIL-002",
        category="Oils & Ghee",
        quantity=20.0,
        unit="litre",
        purchase_price=120.0,
        selling_price=140.0,
        minimum_stock_level=5.0,
        is_active=True,
    )
    db.add(prod2)
    db.commit()
    db.refresh(prod2)

    initial_qty1 = sample_product.quantity
    initial_qty2 = prod2.quantity

    sale_payload = {
        "payment_method": "CASH",
        "notes": "Evening walk-in customer",
        "items": [
            {"product_id": sample_product.id, "quantity": 4.0},
            {"product_id": prod2.id, "quantity": 2.0},
        ],
    }

    # Expected: 4 * 60.0 + 2 * 140.0 = 240 + 280 = 520.0
    expected_total = 520.0

    response = client.post("/api/sales", json=sale_payload)
    assert response.status_code == status.HTTP_201_CREATED
    sale_data = response.json()

    assert sale_data["total_amount"] == expected_total
    assert sale_data["status"] == "COMPLETED"
    assert sale_data["payment_method"] == "CASH"
    assert len(sale_data["items"]) == 2

    # Verify snapshots
    item1 = next(i for i in sale_data["items"] if i["product_id"] == sample_product.id)
    assert item1["unit_price"] == sample_product.selling_price
    assert item1["product_name_snapshot"] == sample_product.name
    assert item1["line_total"] == 240.0

    # Verify inventory was deducted
    db.refresh(sample_product)
    db.refresh(prod2)
    assert sample_product.quantity == initial_qty1 - 4.0
    assert prod2.quantity == initial_qty2 - 2.0


def test_sale_atomic_rollback_on_insufficient_stock(client, db, sample_product):
    """Verify that if one item in a multi-item sale fails, the entire transaction rolls back."""
    prod2 = Product(
        name="Low Stock Dal",
        sku="TEST-DAL-LOW",
        category="Dal",
        quantity=2.0,  # Only 2 available
        unit="kg",
        purchase_price=100.0,
        selling_price=120.0,
        minimum_stock_level=5.0,
        is_active=True,
    )
    db.add(prod2)
    db.commit()
    db.refresh(prod2)

    initial_qty1 = sample_product.quantity
    initial_qty2 = prod2.quantity

    sale_payload = {
        "payment_method": "CASH",
        "items": [
            {"product_id": sample_product.id, "quantity": 5.0},  # Has 50, would succeed
            {"product_id": prod2.id, "quantity": 10.0},          # Has only 2, WILL FAIL
        ],
    }

    response = client.post("/api/sales", json=sale_payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Insufficient stock" in response.json()["detail"]

    # ATOMICITY CHECK: Ensure product 1 stock was NOT deducted!
    db.refresh(sample_product)
    db.refresh(prod2)
    assert sample_product.quantity == initial_qty1
    assert prod2.quantity == initial_qty2


def test_sale_with_customer_udhaar(client, db, sample_product, sample_customer):
    """Test that CREDIT payment increments customer credit balance."""
    initial_balance = sample_customer.credit_balance
    qty = 2.0
    expected_charge = qty * sample_product.selling_price

    sale_payload = {
        "customer_id": sample_customer.id,
        "payment_method": "CREDIT",
        "notes": "Udhaar for Karthik",
        "items": [
            {"product_id": sample_product.id, "quantity": qty},
        ],
    }

    response = client.post("/api/sales", json=sale_payload)
    assert response.status_code == status.HTTP_201_CREATED

    db.refresh(sample_customer)
    assert sample_customer.credit_balance == initial_balance + expected_charge


def test_get_sales_list_and_detail(client, sample_product):
    """Test querying sales list and retrieving sale by ID."""
    # Create a sale
    create_res = client.post("/api/sales", json={
        "payment_method": "UPI",
        "items": [{"product_id": sample_product.id, "quantity": 1.0}],
    })
    assert create_res.status_code == status.HTTP_201_CREATED
    sale_id = create_res.json()["id"]

    # List sales
    list_res = client.get("/api/sales")
    assert list_res.status_code == status.HTTP_200_OK
    assert list_res.json()["total"] >= 1

    # Get single sale
    detail_res = client.get(f"/api/sales/{sale_id}")
    assert detail_res.status_code == status.HTTP_200_OK
    assert detail_res.json()["id"] == sale_id
    assert detail_res.json()["payment_method"] == "UPI"

