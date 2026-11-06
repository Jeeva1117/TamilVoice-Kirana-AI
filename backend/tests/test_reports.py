"""Test suite for analytics reports."""
from fastapi import status


def test_daily_report(client, sample_product):
    """Test retrieving daily sales report."""
    response = client.get("/api/reports/daily")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_revenue" in data
    assert "total_orders" in data
    assert "daily_breakdown" in data
    assert isinstance(data["daily_breakdown"], list)


def test_products_report(client, sample_product):
    """Test retrieving product performance report."""
    response = client.get("/api/reports/products")
    assert response.status_code == status.HTTP_200_OK
    items = response.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    assert "sku" in items[0]
    assert "revenue" in items[0]


def test_inventory_valuation_report(client, sample_product):
    """Test retrieving inventory valuation report."""
    response = client.get("/api/reports/inventory")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_items" in data
    assert "total_quantity" in data
    assert "total_cost_value" in data
    assert "total_retail_value" in data
    assert "potential_profit" in data
    assert "category_summary" in data
