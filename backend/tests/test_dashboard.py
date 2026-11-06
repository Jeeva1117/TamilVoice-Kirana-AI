"""Test suite for dashboard live metrics."""
from fastapi import status


def test_get_dashboard_metrics(client, sample_product):
    """Test retrieving live dashboard summary with realistic KPIs."""
    # Record a sale so dashboard has sales data
    client.post("/api/sales", json={
        "payment_method": "CASH",
        "items": [{"product_id": sample_product.id, "quantity": 3.0}]
    })

    response = client.get("/api/dashboard")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify KPI structure
    kpis = data["kpis"]
    assert "today_sales" in kpis
    assert "today_orders" in kpis
    assert "low_stock_count" in kpis
    assert "out_of_stock_count" in kpis
    assert "total_products" in kpis
    assert "total_inventory_value" in kpis

    assert kpis["today_orders"] >= 1
    assert kpis["today_sales"] >= 180.0

    # Verify top products and recent activity lists
    assert isinstance(data["top_products"], list)
    assert isinstance(data["recent_activities"], list)
    assert isinstance(data["sales_by_category"], dict)
    assert isinstance(data["hourly_sales"], list)
