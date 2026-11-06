"""Test suite for stock adjustment operations."""
from fastapi import status


def test_stock_adjust_add(client, sample_product):
    """Test adding stock to an existing product."""
    initial_qty = sample_product.quantity
    payload = {
        "adjustment_type": "ADD",
        "quantity": 25.0,
        "reason": "New wholesale delivery",
    }
    response = client.post(f"/api/inventory/{sample_product.id}/adjust", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["previous_quantity"] == initial_qty
    assert data["new_quantity"] == initial_qty + 25.0
    assert data["movement_type"] == "ADJUSTMENT_ADD"


def test_stock_adjust_remove(client, sample_product):
    """Test reducing stock from an existing product."""
    initial_qty = sample_product.quantity
    payload = {
        "adjustment_type": "REMOVE",
        "quantity": 10.0,
        "reason": "Damaged pack",
    }
    response = client.post(f"/api/inventory/{sample_product.id}/adjust", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["previous_quantity"] == initial_qty
    assert data["new_quantity"] == initial_qty - 10.0
    assert data["movement_type"] == "ADJUSTMENT_REMOVE"


def test_stock_adjust_set(client, sample_product):
    """Test resetting stock to an absolute value."""
    payload = {
        "adjustment_type": "SET",
        "quantity": 80.0,
        "reason": "Physical store inventory count",
    }
    response = client.post(f"/api/inventory/{sample_product.id}/adjust", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["new_quantity"] == 80.0
    assert data["movement_type"] == "SET_STOCK"


def test_stock_adjust_insufficient_stock(client, sample_product):
    """Test that removing more stock than available fails with 400."""
    payload = {
        "adjustment_type": "REMOVE",
        "quantity": sample_product.quantity + 50.0,  # exceeds available stock
        "reason": "Overselling attempt",
    }
    response = client.post(f"/api/inventory/{sample_product.id}/adjust", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Insufficient stock" in response.json()["detail"]


def test_stock_movement_history(client, sample_product):
    """Test reading audit movements for a product."""
    # Perform an adjustment first
    client.post(
        f"/api/inventory/{sample_product.id}/adjust",
        json={"adjustment_type": "ADD", "quantity": 15.0, "reason": "Test movement audit"}
    )
    # Check history
    response = client.get(f"/api/inventory/{sample_product.id}/movements")
    assert response.status_code == status.HTTP_200_OK
    movements = response.json()
    assert len(movements) >= 1
    assert movements[0]["movement_type"] == "ADJUSTMENT_ADD"
    assert movements[0]["quantity"] == 15.0

