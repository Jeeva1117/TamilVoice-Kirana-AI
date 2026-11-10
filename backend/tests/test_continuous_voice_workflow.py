"""End-to-End Test Suite for Continuous Voice Workflow, Session Context, and Kirana DB Persistence.

Verifies the 12-step Showcase Workflow:
1. Add/Verify test product ("Test Atta") in SQLite catalog.
2. Add 3 kg stock via voice command ("Rice stock-la 3 kilo add pannunga").
3. Voice confirmation ("Aama").
4. Contextual relative stock addition ("Innum 5 kilo add pannunga").
5. Voice stock query ("Rice stock evlo irukku?").
6. Multi-item customer sale command ("Customer-ku 1 kilo tomato, 2 kilo onion, 3 kilo rice, 2 litre milk, 2 packet sugar, 2 packet tea powder sale pannunga").
7. Bill preview generation (₹501).
8. Voice confirmation of sale ("Aama").
9. Atomic SQLite stock deduction verification across all 6 products.
10. Daily sales voice report ("Innaiku sales evlo?").
11. Backend restart simulation (fresh SessionLocal engine connection).
12. Verification of persistent values directly in SQLite kirana_ai.db.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest
import sqlite3
import uuid
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.product import Product
from backend.app.models.sale import Sale


client = TestClient(app)


def test_continuous_voice_shopkeeper_workflow():
    session_id = f"test_sess_{uuid.uuid4().hex[:8]}"

    # Setup baseline stocks in DB
    db = SessionLocal()
    # Baseline for Rice
    rice = db.query(Product).filter(Product.name.like("%Rice%")).first()
    if not rice:
        rice = Product(
            name="Ponni Boiled Rice",
            sku="RICE-001",
            category="Grains & Flours",
            quantity=10.0,
            unit="kg",
            purchase_price=45.0,
            selling_price=55.0,
            minimum_stock_level=10.0,
            is_active=True
        )
        db.add(rice)
    else:
        rice.quantity = 10.0
        rice.selling_price = 55.0
        rice.is_active = True

    # Setup 6 Kirana items for billing test
    items_map = {
        "Tomato": (25.0, 40.0, "kg", "TOM-001"),
        "Onion": (30.0, 35.0, "kg", "ONI-001"),
        "Milk": (20.0, 28.0, "litre", "MLK-001"),
        "Sugar": (25.0, 45.0, "kg", "SUG-001"),
        "Tea Powder": (20.0, 40.0, "packet", "TEA-001"),
    }
    for name, (qty, price, unit, sku) in items_map.items():
        prod = db.query(Product).filter(Product.name == name).first()
        if not prod:
            prod = Product(
                name=name,
                sku=sku,
                category="Groceries",
                quantity=qty,
                unit=unit,
                purchase_price=price * 0.8,
                selling_price=price,
                minimum_stock_level=5.0,
                is_active=True
            )
            db.add(prod)
        else:
            prod.quantity = qty
            prod.selling_price = price
            prod.is_active = True
    db.commit()
    db.close()

    # -------------------------------------------------------------
    # STEP 1: Add a test product ("Test Atta") via API/DB
    # -------------------------------------------------------------
    db = SessionLocal()
    test_atta = db.query(Product).filter(Product.name == "Test Atta").first()
    if not test_atta:
        test_atta = Product(
            name="Test Atta",
            sku="TEST-ATTA-01",
            category="Grains & Flours",
            quantity=5.0,
            unit="kg",
            purchase_price=35.0,
            selling_price=45.0,
            minimum_stock_level=5.0,
            is_active=True
        )
        db.add(test_atta)
        db.commit()
    assert test_atta.id is not None
    print("\n[Step 1 PASS] Test product registered in catalog:", test_atta.name)
    db.close()

    # -------------------------------------------------------------
    # STEP 2: Add 3 kg stock via voice command ("Rice stock-la 3 kilo add pannunga")
    # -------------------------------------------------------------
    payload_step2 = {
        "text": "Rice stock-la 3 kilo add pannunga",
        "session_id": session_id,
        "allow_mock": True
    }
    res2 = client.post("/api/ai/interpret", json=payload_step2).json()
    assert res2["success"] is True
    assert res2["requires_confirmation"] is True
    assert res2["confirmation_preview"] is not None
    assert ("add pannalama" in res2["message_ta"].lower() or "சேர்க்கிறேன்" in res2["message_ta"])
    action_id = res2["confirmation_preview"]["action_id"]
    context = res2.get("context")
    assert context is not None
    assert context.get("pending_action_id") == action_id
    print("[Step 2 PASS] Initial stock command requires confirmation:", res2["message_ta"])

    # -------------------------------------------------------------
    # STEP 3: Confirm the update ("Aama")
    # -------------------------------------------------------------
    payload_step3 = {
        "text": "Aama",
        "session_id": session_id,
        "context": context,
        "allow_mock": True
    }
    res3 = client.post("/api/ai/interpret", json=payload_step3).json()
    assert res3["success"] is True
    assert res3["intent"]["intent"] == "CONFIRM_ACTION"
    assert ("add panniyachu" in res3["message_ta"].lower() or "சேர்க்கப்பட்டது" in res3["message_ta"])
    assert "13" in res3["message_ta"]
    context = res3.get("context")
    print("[Step 3 PASS] Confirmed update via voice:", res3["message_ta"])

    # Verify SQLite stock is now 13 kg
    db = SessionLocal()
    rice = db.query(Product).filter(Product.name.like("%Rice%")).first()
    assert rice.quantity == 13.0
    db.close()

    # -------------------------------------------------------------
    # STEP 4: Add another 5 kg using contextual voice ("Innum 5 kilo add pannunga")
    # -------------------------------------------------------------
    payload_step4 = {
        "text": "Innum 5 kilo add pannunga",
        "session_id": session_id,
        "context": context,
        "allow_mock": True
    }
    res4 = client.post("/api/ai/interpret", json=payload_step4).json()
    assert res4["success"] is True
    assert "18" in res4["message_ta"]
    context = res4.get("context")
    print("[Step 4 PASS] Contextual follow-up executed:", res4["message_ta"])

    # Verify SQLite stock is now 18 kg
    db = SessionLocal()
    rice = db.query(Product).filter(Product.name.like("%Rice%")).first()
    assert rice.quantity == 18.0
    db.close()

    # -------------------------------------------------------------
    # STEP 5: Check stock through voice ("Rice stock evlo irukku?")
    # -------------------------------------------------------------
    payload_step5 = {
        "text": "Rice stock evlo irukku?",
        "session_id": session_id,
        "context": context,
        "allow_mock": True
    }
    res5 = client.post("/api/ai/interpret", json=payload_step5).json()
    assert res5["success"] is True
    assert "18" in res5["message_ta"]
    print("[Step 5 PASS] Stock query response:", res5["message_ta"])

    # -------------------------------------------------------------
    # STEP 6: Sell multiple products ("Customer-ku 1 kilo tomato...")
    # -------------------------------------------------------------
    cmd_multi_sale = "Customer-ku 1 kilo tomato, 2 kilo onion, 3 kilo rice, 2 litre milk, 2 packet sugar, 2 packet tea powder sale pannunga"
    payload_step6 = {
        "text": cmd_multi_sale,
        "session_id": session_id,
        "context": context,
        "allow_mock": True
    }
    res6 = client.post("/api/ai/interpret", json=payload_step6).json()
    assert res6["success"] is True
    assert res6["requires_confirmation"] is True
    preview = res6["confirmation_preview"]
    assert preview is not None

    # -------------------------------------------------------------
    # STEP 7: Generate bill preview (₹501 total)
    # -------------------------------------------------------------
    assert preview["estimated_total"] == 501.0
    assert len(preview["items"]) == 6
    sale_action_id = preview["action_id"]
    context = res6.get("context")
    print(f"[Step 6 & 7 PASS] Bill preview created: ₹{preview['estimated_total']} across {len(preview['items'])} items.")

    # -------------------------------------------------------------
    # STEP 8: Confirm sale ("Aama")
    # -------------------------------------------------------------
    payload_step8 = {
        "text": "Aama",
        "session_id": session_id,
        "context": context,
        "allow_mock": True
    }
    res8 = client.post("/api/ai/interpret", json=payload_step8).json()
    assert res8["success"] is True
    assert res8["intent"]["intent"] == "CONFIRM_ACTION"
    assert "501" in res8["message_ta"]
    print("[Step 8 PASS] Multi-product sale confirmed:", res8["message_ta"])

    # -------------------------------------------------------------
    # STEP 9: Verify stock deduction in SQLite DB
    # -------------------------------------------------------------
    db = SessionLocal()
    p_tomato = db.query(Product).filter(Product.name == "Tomato").first()
    p_onion = db.query(Product).filter(Product.name == "Onion").first()
    p_rice = db.query(Product).filter(Product.name.like("%Rice%")).first()
    p_milk = db.query(Product).filter(Product.name == "Milk").first()
    p_sugar = db.query(Product).filter(Product.name == "Sugar").first()
    p_tea = db.query(Product).filter(Product.name == "Tea Powder").first()

    assert p_tomato.quantity == 24.0  # was 25 - 1
    assert p_onion.quantity == 28.0   # was 30 - 2
    assert p_rice.quantity == 15.0    # was 18 - 3
    assert p_milk.quantity == 18.0    # was 20 - 2
    assert p_sugar.quantity == 23.0   # was 25 - 2
    assert p_tea.quantity == 18.0     # was 20 - 2
    db.close()
    print("[Step 9 PASS] All 6 inventory stocks deducted atomically in SQLite DB.")

    # -------------------------------------------------------------
    # STEP 10: Query daily sales ("Innaiku sales evlo?")
    # -------------------------------------------------------------
    payload_step10 = {
        "text": "Innaiku sales evlo?",
        "session_id": session_id,
        "allow_mock": True
    }
    res10 = client.post("/api/ai/interpret", json=payload_step10).json()
    assert res10["success"] is True
    assert ("sales" in res10["message_ta"].lower() or "விற்பனை" in res10["message_ta"])
    print("[Step 10 PASS] Daily sales query answered:", res10["message_ta"])

    # -------------------------------------------------------------
    # STEP 11: Simulate backend restart (fresh SQLite connection)
    # -------------------------------------------------------------
    fresh_db = SessionLocal()
    fresh_sale = fresh_db.query(Sale).order_by(Sale.id.desc()).first()
    assert fresh_sale is not None
    assert fresh_sale.total_amount == 501.0
    fresh_db.close()
    print("[Step 11 PASS] Backend database reconnection simulated successfully.")

    # -------------------------------------------------------------
    # STEP 12: Verify persistent SQLite values in kirana_ai.db
    # -------------------------------------------------------------
    conn = sqlite3.connect("kirana_ai.db")
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM products WHERE name LIKE '%Rice%'")
    persisted_rice_qty = cursor.fetchone()[0]
    assert persisted_rice_qty == 15.0

    cursor.execute("SELECT COUNT(*) FROM sale_items WHERE sale_id = ?", (fresh_sale.id,))
    item_count = cursor.fetchone()[0]
    assert item_count == 6
    conn.close()
    print("[Step 12 PASS] Direct SQLite verification confirmed persistent data across tables.")
    print("ALL 12 SHOWCASE STEPS VERIFIED 100% SUCCEEDED!")


if __name__ == "__main__":
    test_continuous_voice_shopkeeper_workflow()
