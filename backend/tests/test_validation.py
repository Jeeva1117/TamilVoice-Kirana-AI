"""End-to-End System Validation & Demo Readiness Tests.
Validates all requirements for TamilVoice Kirana AI:
- Controlled products: Rice (₹60/kg, 20kg), Sugar (₹45/kg, 10kg)
- Sales execution & inventory deduction: 2kg Rice sale (₹120) reducing stock to 18kg
- Overselling prevention: rejection with 400 Insufficient Stock
- 6 Gemini Intent commands including missing product clarification safety
- Safe Mode A Mock voice STT & TTS with 0 paid credit consumption
- Customer credit / Udhaar payment settlement
- Business reports and downloadable CSV exports
- Store settings persistence
- Test runner endpoint validation
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.config import settings
from backend.app.models.product import Product
from backend.app.models.customer import Customer
from backend.app.models.sale import Sale
from backend.app.models.stock_movement import StockMovement
from backend.app.schemas.ai import CommandIntent, CommandEntities, IntentCategory


def _seed_controlled_products(db: Session) -> tuple:
    """Ensure Rice (20kg @ ₹60) and Sugar (10kg @ ₹45) exist in the active test session."""
    rice = db.query(Product).filter(Product.name.ilike("%rice%")).first()
    if not rice:
        rice = Product(
            sku="KIR-RICE-01",
            name="Ponni Boiled Rice",
            name_ta="பொன்னி புழுங்கல் அரிசி",
            category="Grains & Rice",
            quantity=20.0,
            unit="kg",
            purchase_price=48.0,
            selling_price=60.0,
            minimum_stock_level=5.0,
            is_active=True,
        )
        db.add(rice)
    else:
        rice.quantity = 20.0
        rice.selling_price = 60.0
        rice.purchase_price = 48.0

    sugar = db.query(Product).filter(Product.name.ilike("%sugar%")).first()
    if not sugar:
        sugar = Product(
            sku="KIR-SUGAR-01",
            name="Refined White Sugar",
            name_ta="சர்க்கரை",
            category="Staples",
            quantity=10.0,
            unit="kg",
            purchase_price=36.0,
            selling_price=45.0,
            minimum_stock_level=3.0,
            is_active=True,
        )
        db.add(sugar)
    else:
        sugar.quantity = 10.0
        sugar.selling_price = 45.0
        sugar.purchase_price = 36.0

    db.commit()
    db.refresh(rice)
    db.refresh(sugar)
    return rice, sugar


# =============================================================================
# 1. Controlled Inventory Tests (Rice 20kg @ ₹60, Sugar 10kg @ ₹45)
# =============================================================================
def test_validation_controlled_inventory_products(client: TestClient, db: Session):
    """Verify controlled products exist or can be seeded with exact specs."""
    rice, sugar = _seed_controlled_products(db)
    assert rice.quantity == 20.0
    assert rice.selling_price == 60.0
    assert sugar.quantity == 10.0
    assert sugar.selling_price == 45.0


# =============================================================================
# 2. Sales Workflow: Rice 2kg Sale -> Stock 20kg to 18kg (Total ₹120)
# =============================================================================
def test_validation_sales_workflow_rice_deduction(client: TestClient, db: Session):
    """
    Test sales workflow:
    Rice 2kg × ₹60 = ₹120.
    Stock decreases from 20kg to 18kg.
    """
    rice, _ = _seed_controlled_products(db)

    sale_payload = {
        "items": [{"product_id": rice.id, "quantity": 2.0}],
        "payment_method": "CASH",
        "notes": "Controlled Rice Sale Test"
    }
    response = client.post("/api/sales", json=sale_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["total_amount"] == 120.0
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 2.0
    assert data["items"][0]["unit_price"] == 60.0
    assert data["items"][0]["line_total"] == 120.0

    # Verify stock reduction in database
    db.refresh(rice)
    assert rice.quantity == 18.0

    # Verify StockMovement audit log
    movement = (
        db.query(StockMovement)
        .filter(StockMovement.product_id == rice.id, StockMovement.movement_type == "SALE")
        .order_by(StockMovement.id.desc())
        .first()
    )
    assert movement is not None
    assert abs(movement.quantity) == 2.0
    assert movement.previous_quantity == 20.0
    assert movement.new_quantity == 18.0


# =============================================================================
# 3. Overselling & Negative Stock Boundary Prevention
# =============================================================================
def test_validation_overselling_prevention(client: TestClient, db: Session):
    """Selling more than available inventory must be rejected with 400 and zero stock change."""
    rice, _ = _seed_controlled_products(db)
    current_stock = rice.quantity

    sale_payload = {
        "items": [{"product_id": rice.id, "quantity": current_stock + 100.0}],
        "payment_method": "CASH"
    }
    response = client.post("/api/sales", json=sale_payload)
    assert response.status_code == 400
    assert "Insufficient stock" in response.json()["detail"]

    db.refresh(rice)
    assert rice.quantity == current_stock


# =============================================================================
# 4. Gemini Intent Command 1: "Innaiku 5 kilo rice stock add pannunga."
# =============================================================================
def test_validation_gemini_cmd_1_add_stock(client: TestClient, db: Session):
    """Command 1: 'Innaiku 5 kilo rice stock add pannunga.' -> ADD_STOCK 5kg Rice."""
    rice, _ = _seed_controlled_products(db)

    mock_intent = CommandIntent(
        intent=IntentCategory.ADD_STOCK,
        original_text="Innaiku 5 kilo rice stock add pannunga.",
        normalized_text="Add 5 kg rice stock today.",
        entities=CommandEntities(product_name="rice", quantity=5.0, unit="kg", date="today"),
        requires_clarification=False,
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock_key_xyz"), \
         patch("backend.app.services.ai_service.gemini_client.generate_intent_async", new=AsyncMock(return_value=mock_intent)):
        response = client.post("/api/ai/interpret", json={"text": "Innaiku 5 kilo rice stock add pannunga."})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["requires_confirmation"] is True
        assert data["confirmation_preview"]["action"] == "ADD_STOCK"
        assert data["confirmation_preview"]["quantity"] == 5.0
        assert data["confirmation_preview"]["unit"] == "kg"
        assert data["confirmation_preview"]["projected_stock"] == rice.quantity + 5.0


# =============================================================================
# 5. Gemini Intent Command 2: "Rice stock evlo irukku?"
# =============================================================================
def test_validation_gemini_cmd_2_check_stock(client: TestClient, db: Session):
    """Command 2: 'Rice stock evlo irukku?' -> CHECK_STOCK."""
    rice, _ = _seed_controlled_products(db)

    mock_intent = CommandIntent(
        intent=IntentCategory.CHECK_STOCK,
        original_text="Rice stock evlo irukku?",
        normalized_text="How much rice stock is available?",
        entities=CommandEntities(product_name="rice"),
        requires_clarification=False,
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock_key_xyz"), \
         patch("backend.app.services.ai_service.gemini_client.generate_intent_async", new=AsyncMock(return_value=mock_intent)):
        response = client.post("/api/ai/interpret", json={"text": "Rice stock evlo irukku?"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["requires_confirmation"] is False
        assert data["query_result"]["stock"] == rice.quantity


# =============================================================================
# 6. Gemini Intent Command 3: "Sugar stock kammiya irukka?"
# =============================================================================
def test_validation_gemini_cmd_3_low_stock(client: TestClient, db: Session):
    """Command 3: 'Sugar stock kammiya irukka?' -> LOW_STOCK_QUERY / CHECK_STOCK."""
    _, sugar = _seed_controlled_products(db)

    mock_intent = CommandIntent(
        intent=IntentCategory.CHECK_STOCK,
        original_text="Sugar stock kammiya irukka?",
        normalized_text="Is sugar stock low?",
        entities=CommandEntities(product_name="sugar"),
        requires_clarification=False,
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock_key_xyz"), \
         patch("backend.app.services.ai_service.gemini_client.generate_intent_async", new=AsyncMock(return_value=mock_intent)):
        response = client.post("/api/ai/interpret", json={"text": "Sugar stock kammiya irukka?"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "sugar" in data["message"].lower() or "சர்க்கரை" in data.get("message_ta", "")


# =============================================================================
# 7. Gemini Intent Command 4: "Innaiku rice 2 kilo sell pannunga."
# =============================================================================
def test_validation_gemini_cmd_4_sell_product(client: TestClient, db: Session):
    """Command 4: 'Innaiku rice 2 kilo sell pannunga.' -> SELL_PRODUCT 2kg Rice."""
    rice, _ = _seed_controlled_products(db)
    curr_qty = rice.quantity

    mock_intent = CommandIntent(
        intent=IntentCategory.SELL_PRODUCT,
        original_text="Innaiku rice 2 kilo sell pannunga.",
        normalized_text="Sell 2 kg rice today.",
        entities=CommandEntities(product_name="rice", quantity=2.0, unit="kg", date="today"),
        requires_clarification=False,
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock_key_xyz"), \
         patch("backend.app.services.ai_service.gemini_client.generate_intent_async", new=AsyncMock(return_value=mock_intent)):
        response = client.post("/api/ai/interpret", json={"text": "Innaiku rice 2 kilo sell pannunga."})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["requires_confirmation"] is True
        assert data["confirmation_preview"]["action"] == "SELL_PRODUCT"
        assert data["confirmation_preview"]["quantity"] == 2.0
        assert data["confirmation_preview"]["estimated_total"] == 2.0 * rice.selling_price
        assert data["confirmation_preview"]["projected_stock"] == curr_qty - 2.0

        # Verify database is UNCHANGED before confirmation
        db.refresh(rice)
        assert rice.quantity == curr_qty


# =============================================================================
# 8. Gemini Intent Command 5: "Show today's sales."
# =============================================================================
def test_validation_gemini_cmd_5_sales_report(client: TestClient, db: Session):
    """Command 5: 'Show today's sales.' -> SALES_REPORT read-only."""
    _seed_controlled_products(db)

    mock_intent = CommandIntent(
        intent=IntentCategory.SALES_REPORT,
        original_text="Show today's sales.",
        normalized_text="Show today's sales.",
        entities=CommandEntities(date="today"),
        requires_clarification=False,
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock_key_xyz"), \
         patch("backend.app.services.ai_service.gemini_client.generate_intent_async", new=AsyncMock(return_value=mock_intent)):
        response = client.post("/api/ai/interpret", json={"text": "Show today's sales."})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["requires_confirmation"] is False
        assert "today_sales" in data["query_result"]


# =============================================================================
# 9. Gemini Intent Command 6: "Add 5 kg." (Clarification Safety)
# =============================================================================
def test_validation_gemini_cmd_6_missing_product_clarification(client: TestClient, db: Session):
    """
    Command 6: 'Add 5 kg.' (Missing Product Name)
    CRITICAL SAFETY REQUIREMENT:
    System must NOT silently choose a product; it must request clarification!
    Database must NOT be modified.
    """
    _seed_controlled_products(db)
    prods_before = [(p.id, p.quantity) for p in db.query(Product).all()]

    mock_intent = CommandIntent(
        intent=IntentCategory.ADD_STOCK,
        original_text="Add 5 kg.",
        normalized_text="Add 5 kg.",
        entities=CommandEntities(product_name=None, quantity=5.0, unit="kg"),
        requires_clarification=True,
        clarification_question="Which product would you like to add 5 kg of?",
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock_key_xyz"), \
         patch("backend.app.services.ai_service.gemini_client.generate_intent_async", new=AsyncMock(return_value=mock_intent)):
        response = client.post("/api/ai/interpret", json={"text": "Add 5 kg."})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["requires_confirmation"] is False
        assert data["intent"]["requires_clarification"] is True
        assert "Which product" in data["message"]

    # Verify zero database changes
    prods_after = [(p.id, p.quantity) for p in db.query(Product).all()]
    assert prods_before == prods_after


# =============================================================================
# 10. Two-Step Confirmation Safety (Cancel leaves DB untouched)
# =============================================================================
def test_validation_two_step_cancel_safety(client: TestClient, db: Session):
    """Cancelling a pending action leaves database completely unchanged."""
    rice, _ = _seed_controlled_products(db)
    initial_stock = rice.quantity

    mock_intent = CommandIntent(
        intent=IntentCategory.ADD_STOCK,
        original_text="Add 10 kg rice",
        normalized_text="Add 10 kg rice",
        entities=CommandEntities(product_name="rice", quantity=10.0, unit="kg"),
        requires_clarification=False,
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock_key_xyz"), \
         patch("backend.app.services.ai_service.gemini_client.generate_intent_async", new=AsyncMock(return_value=mock_intent)):
        res = client.post("/api/ai/interpret", json={"text": "Add 10 kg rice"})
        data = res.json()
        action_id = data["confirmation_preview"]["action_id"]

        # Cancel the pending action
        cancel_res = client.post("/api/ai/cancel", json={"action_id": action_id})
        assert cancel_res.status_code == 200
        assert cancel_res.json()["success"] is True

        # Database stock must be strictly untouched
        db.refresh(rice)
        assert rice.quantity == initial_stock


# =============================================================================
# 11. Mode A Mock Voice STT & TTS (0 Credits Consumed)
# =============================================================================
def test_validation_voice_stt_and_tts_mode_a(client: TestClient):
    """Verify STT and TTS work in safe mock mode without consuming paid Gnani credits."""
    # STT Test (Mock audio with valid length > 200 bytes)
    wav_bytes = (
        b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        + (b"\x00" * 300)
    )
    files = {"file": ("test.wav", wav_bytes, "audio/wav")}
    with patch.object(settings, "GNANI_API_KEY", ""):
        response = client.post("/api/voice/transcribe", files=files, data={"language": "ta-IN"})
        assert response.status_code == 200
        stt_data = response.json()
        assert "transcript" in stt_data
        assert stt_data.get("provider") == "mock_prisma"

    # TTS Test (Mock synthesis)
    tts_payload = {"text": "வணக்கம்! அரிசி இருப்பு அப்டேட் செய்யப்பட்டது.", "language": "ta-IN", "speed": 1.0}
    with patch.object(settings, "GNANI_API_KEY", ""):
        tts_res = client.post("/api/voice/speak", json=tts_payload)
        assert tts_res.status_code == 200
        assert tts_res.headers["content-type"] == "audio/wav"
        assert len(tts_res.content) > 44  # Valid WAV header size


# =============================================================================
# 12. Customer Khata & Udhaar Payment Settlement
# =============================================================================
def test_validation_customer_udhaar_payment(client: TestClient, db: Session):
    """Test Udhaar payment settlement reduces balance."""
    cust = Customer(name="Kandasamy M.", phone="+91 98765 43210", credit_balance=350.0)
    db.add(cust)
    db.commit()
    db.refresh(cust)

    payment_payload = {
        "amount": 150.0,
        "payment_method": "CASH",
        "notes": "Partial weekly settlement"
    }
    res = client.post(f"/api/customers/{cust.id}/payment", json=payment_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["amount_paid"] == 150.0
    assert data["previous_balance"] == 350.0
    assert data["remaining_balance"] == 200.0

    db.refresh(cust)
    assert cust.credit_balance == 200.0


# =============================================================================
# 13. Reports CSV Export Generation
# =============================================================================
def test_validation_reports_csv_export(client: TestClient, db: Session):
    """Test downloadable CSV exports for products, daily sales, and inventory."""
    _seed_controlled_products(db)
    for rtype in ["products", "daily", "inventory"]:
        res = client.get(f"/api/reports/export/csv?report_type={rtype}")
        assert res.status_code == 200
        assert res.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment; filename=" in res.headers["content-disposition"]
        lines = res.text.strip().split("\n")
        assert len(lines) >= 1  # Contains header


# =============================================================================
# 14. Store Settings Persistence
# =============================================================================
def test_validation_store_settings(client: TestClient):
    """Test store settings retrieval and update."""
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "shop_name" in data
    assert "currency_symbol" in data

    # Update phone number
    update_res = client.put("/api/settings", json={"phone": "+91 99999 88888"})
    assert update_res.status_code == 200
    assert update_res.json()["phone"] == "+91 99999 88888"


# =============================================================================
# 15. In-App System Test Runner Endpoint
# =============================================================================
def test_validation_system_test_runner_endpoint(client: TestClient):
    """Test that POST /api/test/run executes cleanly in Mode A without credit burn."""
    res = client.post("/api/test/run", json={"test_id": "all", "mode": "mock"})
    assert res.status_code == 200
    data = res.json()
    assert data["overall_status"] == "PASS"
    assert data["failed_tests"] == 0
    assert data["total_tests"] >= 12
    assert data["gnani_credits_estimated_remaining"] == 5000
    assert data["gnani_credit_usage_note"] == "Usage not available from provider API"
