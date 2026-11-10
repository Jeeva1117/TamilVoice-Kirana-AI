"""End-to-end Verification for Section 10 Requirements:
- Stock Addition: 20 kg + 10 kg = 30 kg
- Stock Addition Again: 30 kg + 5 kg = 35 kg
- Sale: 35 kg - 12 kg = 23 kg
- Stock Query: Returns 23 kg from database
- Billing: Real price and stock calculation
- Conversation: 'Thank you' -> natural response
- Persistence: Verify 23 kg persists in database
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.main import app
from backend.app.database import SessionLocal, get_db
from backend.app.models.product import Product
from backend.app.models.stock_movement import StockMovement
from backend.app.models.sale import Sale


def test_section10_complete_workflow():
    client = TestClient(app)
    db: Session = SessionLocal()

    try:
        # Step 0: Set baseline stock of Rice to exactly 20.0 kg
        rice = db.query(Product).filter(Product.name.ilike("%Rice%")).first()
        assert rice is not None, "Ponni Boiled Rice must exist in catalog"
        rice.quantity = 20.0
        rice.selling_price = 55.0
        db.commit()
        db.refresh(rice)
        assert rice.quantity == 20.0

        # Step 1: Stock Addition (20 kg + 10 kg = 30 kg)
        # Interpret addition command
        res1 = client.post("/api/ai/interpret", json={"text": "10 kg rice stock-la add pannunga"})
        assert res1.status_code == 200
        d1 = res1.json()
        assert d1["success"] is True
        assert d1["requires_confirmation"] is True
        action_id_1 = d1["confirmation_preview"]["action_id"]

        # Confirm addition
        conf1 = client.post("/api/ai/confirm", json={"action_id": action_id_1})
        assert conf1.status_code == 200
        cd1 = conf1.json()
        assert cd1["new_stock"] == 30.0
        assert "30" in cd1["message_ta"] or "30" in cd1["message"]

        # Step 2: Stock Addition Again (30 kg + 5 kg = 35 kg)
        res2 = client.post("/api/ai/interpret", json={"text": "5 kg rice add pannunga"})
        assert res2.status_code == 200
        d2 = res2.json()
        action_id_2 = d2["confirmation_preview"]["action_id"]

        conf2 = client.post("/api/ai/confirm", json={"action_id": action_id_2})
        assert conf2.status_code == 200
        cd2 = conf2.json()
        assert cd2["new_stock"] == 35.0
        assert "35" in cd2["message_ta"] or "35" in cd2["message"]

        # Step 3: Billing & Sale Deduction (35 kg - 12 kg = 23 kg)
        res3 = client.post("/api/ai/interpret", json={"text": "Customer-ku 12 kg rice bill podu"})
        assert res3.status_code == 200
        d3 = res3.json()
        assert d3["requires_confirmation"] is True
        preview = d3["confirmation_preview"]
        assert preview["action"] == "SELL_PRODUCT"
        assert preview["quantity"] == 12.0
        assert preview["current_stock"] == 35.0
        assert preview["projected_stock"] == 23.0
        assert preview["estimated_total"] == round(12.0 * 55.0, 2)  # 660.0
        action_id_3 = preview["action_id"]

        conf3 = client.post("/api/ai/confirm", json={"action_id": action_id_3})
        assert conf3.status_code == 200
        cd3 = conf3.json()
        assert cd3["action"] == "SELL_PRODUCT"
        assert cd3["previous_stock"] == 35.0
        assert cd3["new_stock"] == 23.0
        assert cd3["total_amount"] == 660.0
        assert "23" in cd3["message_ta"]

        # Step 4: Stock Query (Return 23 kg from database)
        res4 = client.post("/api/ai/interpret", json={"text": "Rice stock evlo irukku?"})
        assert res4.status_code == 200
        d4 = res4.json()
        assert d4["query_result"]["stock"] == 23.0
        assert "23" in d4["message_ta"] or "23" in d4["message"]

        # Step 5: Conversation Politeness ('Thank you' -> natural response, no product question)
        res5 = client.post("/api/ai/interpret", json={"text": "Okay, thank you so much"})
        assert res5.status_code == 200
        d5 = res5.json()
        assert d5["intent"]["intent"] == "THANK_YOU"
        assert d5["intent"]["requires_clarification"] is False
        assert "welcome" in d5["message_ta"].lower() or "உதவி" in d5["message_ta"]

        # Step 6: Database Persistence Check
        db.expire_all()
        persisted_rice = db.query(Product).filter(Product.name.ilike("%Rice%")).first()
        assert persisted_rice.quantity == 23.0, f"Expected 23.0 kg in database, got {persisted_rice.quantity}"

        # Verify audit movements
        recent_movements = db.query(StockMovement).filter(StockMovement.product_id == persisted_rice.id).order_by(StockMovement.id.desc()).limit(3).all()
        assert len(recent_movements) == 3
        assert recent_movements[0].movement_type == "SALE"
        assert recent_movements[0].new_quantity == 23.0
        assert recent_movements[1].movement_type == "ADJUSTMENT_ADD"
        assert recent_movements[1].new_quantity == 35.0
        assert recent_movements[2].movement_type == "ADJUSTMENT_ADD"
        assert recent_movements[2].new_quantity == 30.0

    finally:
        db.close()

