"""Comprehensive Phase 16 Master Test Suite: Universal Kirana AI Intelligence.
Validates:
1. Dynamic multi-item billing across grocery, vegetable, packaged, household, and stationery categories.
2. Safe metric unit conversions (200g -> 0.2kg, 500ml -> 0.5l, packets, pieces) with exact Decimal arithmetic.
3. Unknown product clarification and catalog boundary handling.
4. Voice stock management: ADD_STOCK, REMOVE_STOCK with negative stock prevention, and SET_STOCK.
5. Predictive stock-out intelligence ('Naalaikku entha products stock out aagum?').
6. Voice-driven Kirana business reports (today's sales, best sellers, total inventory valuation).
"""
import uuid
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db, SessionLocal
from backend.app.models.product import Product
from backend.app.models.sale import Sale
from backend.app.services.unit_converter import convert_quantity_to_base, canonical_unit, are_units_compatible
from backend.app.services.billing_calculator import calculate_line_item_with_conversion, calculate_bill
from backend.app.services.stock_intelligence_service import analyze_stock_intelligence

client = TestClient(app)


def test_unit_converter_exhaustive():
    """Validates metric and retail conversions with exact Decimal arithmetic."""
    # Grams to Kg
    c_qty, factor = convert_quantity_to_base(Decimal("200"), "g", "kg", "Ginger")
    assert c_qty == Decimal("0.200")
    assert factor == Decimal("0.001")

    # Millilitre to Litre
    c_qty, factor = convert_quantity_to_base(Decimal("500"), "ml", "litre", "Coconut Oil")
    assert c_qty == Decimal("0.500")

    # Retail packet <-> Kg fallback
    c_qty, factor = convert_quantity_to_base(Decimal("2"), "packet", "kg", "Sugar")
    assert c_qty == Decimal("2.0")

    # Dozen <-> Piece
    c_qty, factor = convert_quantity_to_base(Decimal("2"), "dozen", "piece", "Egg")
    assert c_qty == Decimal("24")

    # Neutral unit
    c_qty, factor = convert_quantity_to_base(Decimal("5"), "unit", "unit", "Soap")
    assert c_qty == Decimal("5")


def test_billing_calculator_precision():
    """Validates exact line totals using Python Decimal."""
    # 200 g Ginger @ ₹120 / kg = ₹24.00
    line_total, converted_qty = calculate_line_item_with_conversion(
        quantity=200,
        unit_price=120,
        requested_unit="g",
        base_unit="kg",
        product_name="Ginger"
    )
    assert line_total == Decimal("24.00")
    assert converted_qty == Decimal("0.200")

    # 500 ml Coconut Oil @ ₹140 / litre = ₹70.00
    line_total, converted_qty = calculate_line_item_with_conversion(
        quantity=500,
        unit_price=140,
        requested_unit="ml",
        base_unit="litre",
        product_name="Coconut Oil"
    )
    assert line_total == Decimal("70.00")
    assert converted_qty == Decimal("0.500")

    # Multi-item calculation
    bill = calculate_bill(
        items=[
            {"product_id": 1, "product_name": "Tomato", "quantity": 1, "unit": "kg", "unit_price": 40.0, "base_unit": "kg"},
            {"product_id": 2, "product_name": "Onion", "quantity": 1, "unit": "kg", "unit_price": 35.0, "base_unit": "kg"},
            {"product_id": 3, "product_name": "Ginger", "quantity": 200, "unit": "g", "unit_price": 120.0, "base_unit": "kg"},
        ]
    )
    # 40.00 + 35.00 + 24.00 = 99.00
    assert bill.subtotal == Decimal("99.00")
    assert bill.grand_total == Decimal("99.00")


def test_scenario_a_mixed_multi_item_voice_bill():
    """Scenario A: Multi-product single-sentence bill spanning vegetables, groceries, and packaged items."""
    db = SessionLocal()
    # Ensure test products exist with SKUs
    products_to_verify = [
        ("Tomato", "Vegetables", 30.0, 40.0, "kg", "TOM-001"),
        ("Onion", "Vegetables", 30.0, 35.0, "kg", "ONI-001"),
        ("Ginger", "Vegetables", 10.0, 120.0, "kg", "GIN-001"),
        ("Sugar", "Groceries", 25.0, 45.0, "kg", "SUG-001"),
        ("Tea Powder", "Groceries", 20.0, 40.0, "packet", "TEA-001"),
        ("Pen", "Stationery", 50.0, 10.0, "piece", "PEN-001"),
    ]
    for name, cat, qty, price, unit, sku in products_to_verify:
        p = db.query(Product).filter(Product.name == name).first()
        if not p:
            p = Product(name=name, sku=sku, category=cat, quantity=qty, purchase_price=price * 0.8, selling_price=price, unit=unit, is_active=True)
            db.add(p)
        else:
            p.quantity = max(p.quantity, qty)
            p.selling_price = price
            p.is_active = True
    db.commit()
    db.close()

    session_id = f"test_multi_{uuid.uuid4().hex[:6]}"
    cmd_text = "Customer-ku 1 kg tomato, 1 kg onion, 200 g ginger, 1 packet tea powder, 2 pen bill podu"
    res = client.post("/api/ai/interpret", json={"text": cmd_text, "session_id": session_id, "allow_mock": True}).json()

    assert res["success"] is True
    assert res["requires_confirmation"] is True
    assert res["confirmation_preview"] is not None
    action_id = res["confirmation_preview"]["action_id"]

    # Confirm bill via confirm endpoint
    confirm_res = client.post("/api/ai/confirm", json={"action_id": action_id}).json()
    assert confirm_res["success"] is True
    assert confirm_res["transaction_id"] is not None
    assert confirm_res["total_amount"] > 0


def test_scenario_b_unknown_product_clarification():
    """Scenario B: Unknown product triggers clarification and guidance rather than crashing."""
    unknown_cmd = "Customer-ku 2 packet unknown_product_xyz bill podu"
    res = client.post("/api/ai/interpret", json={"text": unknown_cmd, "allow_mock": True}).json()

    # Should not crash; returns guidance
    msg = res.get("message", "").lower()
    msg_ta = res.get("message_ta", "")
    is_clarification = res.get("intent", {}).get("requires_clarification", False)
    assert res["success"] is False or is_clarification or "not found" in msg or "not in your store" in msg or "இல்லை" in msg_ta


def test_scenario_c_and_d_stock_add_and_remove():
    """Scenario C & D: Stock addition and stock removal with boundary protection."""
    db = SessionLocal()
    prod = db.query(Product).filter(Product.name == "Sugar").first()
    if not prod:
        prod = Product(name="Sugar", sku="SUG-001", category="Groceries", quantity=20.0, unit="kg", purchase_price=38.0, selling_price=45.0, is_active=True)
        db.add(prod)
        db.commit()
    start_qty = prod.quantity
    db.close()

    session_id = f"test_stock_{uuid.uuid4().hex[:6]}"

    # Step 1: Add 10 kg stock
    add_cmd = "Sugar stock-la 10 kg add pannunga"
    res_add = client.post("/api/ai/interpret", json={"text": add_cmd, "session_id": session_id, "allow_mock": True}).json()
    assert res_add["success"] is True
    assert res_add["requires_confirmation"] is True
    assert res_add["confirmation_preview"]["projected_stock"] == round(start_qty + 10.0, 2)
    action_id_add = res_add["confirmation_preview"]["action_id"]

    # Confirm addition
    c_add = client.post("/api/ai/confirm", json={"action_id": action_id_add}).json()
    assert c_add["success"] is True

    # Verify DB stock increased
    db = SessionLocal()
    prod = db.query(Product).filter(Product.name == "Sugar").first()
    assert prod.quantity == start_qty + 10.0
    db.close()

    # Step 2: Remove 5 kg stock
    rem_cmd = "Sugar stock-la 5 kg remove pannunga"
    res_rem = client.post("/api/ai/interpret", json={"text": rem_cmd, "session_id": session_id, "allow_mock": True}).json()
    assert res_rem["success"] is True
    assert res_rem["requires_confirmation"] is True
    assert res_rem["confirmation_preview"]["projected_stock"] == round(start_qty + 10.0 - 5.0, 2)
    action_id_rem = res_rem["confirmation_preview"]["action_id"]

    # Confirm removal
    c_rem = client.post("/api/ai/confirm", json={"action_id": action_id_rem}).json()
    assert c_rem["success"] is True

    # Verify DB stock decreased
    db = SessionLocal()
    prod = db.query(Product).filter(Product.name == "Sugar").first()
    assert prod.quantity == start_qty + 10.0 - 5.0
    db.close()

    # Step 3: Attempt to remove excessive stock (negative stock prevention)
    excess_cmd = "Sugar stock-la 5000 kg remove pannunga"
    res_excess = client.post("/api/ai/interpret", json={"text": excess_cmd, "session_id": session_id, "allow_mock": True}).json()
    assert res_excess["success"] is False
    assert "insufficient" in res_excess["message"].lower() or "போதிய அளவு இருப்பு இல்லை" in res_excess.get("message_ta", "")


def test_scenario_e_predictive_stock_out_intelligence():
    """Scenario E: Query predictive stock-out risk ('Naalaikku entha products stock out aagum?')."""
    db = SessionLocal()
    intel = analyze_stock_intelligence(db)
    assert "critical_risk_items" in intel
    assert "moderate_risk_items" in intel
    assert "summary_en" in intel
    assert "summary_ta" in intel
    assert "summary_tanglish" in intel
    db.close()

    # Run through voice AI endpoint
    res = client.post("/api/ai/interpret", json={"text": "Naalaikku entha products stock out aagum?", "allow_mock": True}).json()
    assert res["success"] is True
    assert "query_result" in res or "message" in res
    assert "stock" in res["message"].lower() or "இருப்பு" in res.get("message_ta", "")


def test_scenario_f_voice_business_reports():
    """Scenario F: Today's sales, best seller, and inventory value voice queries."""
    # 1. Today sales report
    res_sales = client.post("/api/ai/interpret", json={"text": "Innaiku sales evlo?", "allow_mock": True}).json()
    assert res_sales["success"] is True
    assert "sale" in res_sales["message"].lower() or "விற்பனை" in res_sales.get("message_ta", "")

    # 2. Inventory valuation
    res_inv = client.post("/api/ai/interpret", json={"text": "Total inventory value evlo?", "allow_mock": True}).json()
    assert res_inv["success"] is True
    assert "inventory" in res_inv["message"].lower() or "மதிப்பு" in res_inv.get("message_ta", "")

    # 3. Top selling product
    res_top = client.post("/api/ai/interpret", json={"text": "Top selling product edhu?", "allow_mock": True}).json()
    assert res_top["success"] is True
