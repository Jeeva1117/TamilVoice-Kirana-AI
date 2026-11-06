"""Test suite for inventory management APIs."""
from fastapi import status


def test_create_product(client):
    """Test creating a new Kirana product."""
    payload = {
        "name": "Tata Salt 1kg",
        "name_ta": "டாடா உப்பு",
        "sku": "SPC-SLT-TEST",
        "category": "Spices & Seasoning",
        "quantity": 30.0,
        "unit": "packet",
        "purchase_price": 22.0,
        "selling_price": 28.0,
        "minimum_stock_level": 10.0,
        "description": "Iodized vacuum salt",
        "is_active": True,
    }
    response = client.post("/api/inventory", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["sku"] == "SPC-SLT-TEST"
    assert data["name"] == "Tata Salt 1kg"
    assert data["stock_status"] == "in_stock"
    assert data["is_low_stock"] is False
    assert data["is_out_of_stock"] is False


def test_reject_duplicate_sku(client, sample_product):
    """Test that creating a product with duplicate SKU is rejected."""
    payload = {
        "name": "Duplicate Product",
        "sku": sample_product.sku,  # same SKU
        "category": "Test",
        "quantity": 10.0,
        "unit": "kg",
        "purchase_price": 40.0,
        "selling_price": 50.0,
        "minimum_stock_level": 5.0,
    }
    response = client.post("/api/inventory", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.json()["detail"]


def test_get_product_by_id(client, sample_product):
    """Test retrieving an existing product."""
    response = client.get(f"/api/inventory/{sample_product.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == sample_product.id
    assert data["sku"] == sample_product.sku


def test_get_product_not_found(client):
    """Test retrieving non-existent product returns 404."""
    response = client.get("/api/inventory/999999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_product(client, sample_product):
    """Test updating product prices and details."""
    payload = {
        "selling_price": 65.0,
        "purchase_price": 54.0,
        "name": "Ponni Boiled Rice Super",
    }
    response = client.put(f"/api/inventory/{sample_product.id}", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["selling_price"] == 65.0
    assert data["purchase_price"] == 54.0
    assert data["name"] == "Ponni Boiled Rice Super"


def test_soft_delete_product(client, sample_product):
    """Test soft-deleting a product."""
    del_resp = client.delete(f"/api/inventory/{sample_product.id}")
    assert del_resp.status_code == status.HTTP_200_OK

    # Once soft-deleted, it should return 404 from active products endpoint
    get_resp = client.get(f"/api/inventory/{sample_product.id}")
    assert get_resp.status_code == status.HTTP_404_NOT_FOUND


def test_filter_and_search_products(client, sample_product):
    """Test search by keyword and category."""
    # Search by keyword
    res = client.get("/api/inventory?search=Ponni")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["total"] >= 1

    # Search by category
    res_cat = client.get("/api/inventory?category=Rice %26 Grains")
    assert res_cat.status_code == status.HTTP_200_OK
    assert res_cat.json()["total"] >= 1

    # Search non-matching
    res_empty = client.get("/api/inventory?search=NonExistentProductXYZ")
    assert res_empty.status_code == status.HTTP_200_OK
    assert res_empty.json()["total"] == 0


def test_list_categories(client, sample_product):
    """Test retrieving unique list of categories."""
    response = client.get("/api/inventory/categories")
    assert response.status_code == status.HTTP_200_OK
    cats = response.json()
    assert isinstance(cats, list)
    assert sample_product.category in cats
