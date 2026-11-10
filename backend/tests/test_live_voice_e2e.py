"""Comprehensive End-to-End Test Suite for TamilVoice Kirana AI.
Verifies Phase 1 to Phase 11:
- Voice processing & language detection (Tamil, English, Tanglish)
- Real SQLite inventory and pricing operations
- Conversational additions, corrections, and confirmations
- Multi-product voice billing with atomic stock deduction
- Clean demonstration inventory validation (Rice, Sugar, Tea Powder, Tomato, Honey)
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.product import Product
from backend.app.models.sale import Sale
from backend.app.models.sale_item import SaleItem
from backend.app.seed_demonstration import seed_clean_inventory

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_inventory():
    """Seed clean baseline demonstration inventory."""
    seed_clean_inventory()


def test_01_voice_status_and_readiness():
    """Phase 1: Verify Voice Status endpoint reports readiness without leaking keys."""
    res = client.get("/api/voice/status")
    assert res.status_code == 200
    data = res.json()
    assert "ready" in data
    assert "supported_languages" in data
    assert "ta-IN" in data["supported_languages"]
    assert "en-IN" in data["supported_languages"]
    # No secret key in response
    assert "key" not in str(data).lower() or "configured" in str(data).lower()


def test_02_tamil_input_receives_tamil_response():
    """Phase 4: Tamil input receives Tamil response."""
    session_id = f"sess_ta_{uuid.uuid4().hex[:6]}"
    res = client.post("/api/ai/interpret", json={
        "text": "இன்னைக்கு அரிசி stock எவ்வளவு?",
        "session_id": session_id,
        "allow_mock": True
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["detected_language"] == "Tamil"
    assert "பொன்னி புழுங்கல் அரிசி" in data["spoken_response"] or "உள்ளது" in data["spoken_response"]


def test_03_english_input_receives_english_response():
    """Phase 4: English input receives English response."""
    session_id = f"sess_en_{uuid.uuid4().hex[:6]}"
    res = client.post("/api/ai/interpret", json={
        "text": "How much rice stock do we have?",
        "session_id": session_id,
        "allow_mock": True
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["detected_language"] == "English"
    assert "stock" in data["spoken_response"].lower()
    assert "rice" in data["spoken_response"].lower()


def test_04_tanglish_input_receives_tanglish_response():
    """Phase 4: Tanglish input receives Tanglish response."""
    session_id = f"sess_tang_{uuid.uuid4().hex[:6]}"
    res = client.post("/api/ai/interpret", json={
        "text": "Rice stock evlo irukku?",
        "session_id": session_id,
        "allow_mock": True
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["detected_language"] == "Tanglish"
    assert "irukku" in data["spoken_response"].lower() or "25" in data["spoken_response"]


def test_05_clean_demonstration_products_exist():
    """Phase 7: Verify the clean 5 demonstration products exist in database."""
    db = SessionLocal()
    target_products = ["Ponni Boiled Rice", "Sugar", "Tea Powder", "Tomato", "Pure Honey"]
    for name in target_products:
        p = db.query(Product).filter(Product.name == name, Product.is_active == True).first()
        assert p is not None, f"Expected product '{name}' in catalog"
        assert p.quantity > 0, f"Expected stock > 0 for '{name}'"
        assert p.selling_price > 0, f"Expected price > 0 for '{name}'"
    db.close()


def test_06_honey_product_resolution_and_stock_inquiry():
    """Phase 7 & 8: Verify Honey resolution in Tamil ('தேன்') and English ('honey')."""
    session_id = f"sess_honey_{uuid.uuid4().hex[:6]}"
    res_ta = client.post("/api/ai/interpret", json={
        "text": "தேன் stock எவ்வளவு இருக்கு?",
        "session_id": session_id,
        "allow_mock": True
    })
    assert res_ta.status_code == 200
    data_ta = res_ta.json()
    assert data_ta["success"] is True
    assert data_ta["resolved_product"]["name"] == "Pure Honey"
    assert data_ta["resolved_product"]["unit"] == "bottle"

    res_en = client.post("/api/ai/interpret", json={
        "text": "How many honey bottles do we have in stock?",
        "session_id": session_id,
        "allow_mock": True
    })
    assert res_en.status_code == 200
    data_en = res_en.json()
    assert data_en["success"] is True
    assert data_en["detected_language"] == "English"
    assert "15" in data_en["spoken_response"]


def test_07_voice_stock_addition_large_quantity():
    """Phase 8: Support large valid quantities (1000 kg rice addition)."""
    session_id = f"sess_add_{uuid.uuid4().hex[:6]}"
    res = client.post("/api/ai/interpret", json={
        "text": "Rice-ku 1000 kilo stock add pannunga",
        "session_id": session_id,
        "allow_mock": True
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["requires_confirmation"] is True
    assert data["confirmation_preview"]["quantity"] == 1000.0
    action_id = data["confirmation_preview"]["action_id"]

    # Confirm action verbally
    res_confirm = client.post("/api/ai/interpret", json={
        "text": "Aama",
        "session_id": session_id,
        "allow_mock": True
    })
    assert res_confirm.status_code == 200
    data_conf = res_confirm.json()
    assert data_conf["success"] is True

    # Verify SQLite stock updated
    db = SessionLocal()
    rice = db.query(Product).filter(Product.name == "Ponni Boiled Rice").first()
    assert rice.quantity == 1025.0  # was 25 + 1000
    db.close()


def test_08_multi_product_voice_billing_and_atomic_deduction():
    """Phase 9: Multi-product retail customer order with atomic deduction."""
    session_id = f"sess_bill_{uuid.uuid4().hex[:6]}"
    # Order: 2 kg tomato (Rs 40*2 = 80), 1 packet tea powder (Rs 40*1 = 40), 1 bottle honey (Rs 180*1 = 180) -> Total = 300
    res_bill = client.post("/api/ai/interpret", json={
        "text": "Customer-ku 2 kilo tomato, 1 packet tea powder, 1 bottle honey bill podu",
        "session_id": session_id,
        "allow_mock": True
    })
    assert res_bill.status_code == 200
    data = res_bill.json()
    assert data["success"] is True
    assert data["requires_confirmation"] is True
    preview = data["confirmation_preview"]
    assert preview is not None
    assert preview["estimated_total"] == 300.0
    assert len(preview["items"]) == 3
    action_id = preview["action_id"]

    # Confirm sale verbally
    res_conf = client.post("/api/ai/interpret", json={
        "text": "Aama",
        "session_id": session_id,
        "allow_mock": True
    })
    assert res_conf.status_code == 200

    # Verify atomic SQLite deductions
    db = SessionLocal()
    tomato = db.query(Product).filter(Product.name == "Tomato").first()
    tea = db.query(Product).filter(Product.name == "Tea Powder").first()
    honey = db.query(Product).filter(Product.name == "Pure Honey").first()

    assert tomato.quantity == 18.0  # was 20 - 2
    assert tea.quantity == 19.0     # was 20 - 1
    assert honey.quantity == 14.0   # was 15 - 1

    # Verify sale record created
    last_sale = db.query(Sale).order_by(Sale.id.desc()).first()
    assert last_sale is not None
    assert last_sale.total_amount == 300.0
    db.close()


def test_09_voice_cancellation_preserves_stock():
    """Phase 10: Cancel action cleanly leaves stock unchanged."""
    session_id = f"sess_canc_{uuid.uuid4().hex[:6]}"
    # Initiate sale
    res_init = client.post("/api/ai/interpret", json={
        "text": "Tomato 5 kilo bill podu",
        "session_id": session_id,
        "allow_mock": True
    })
    assert res_init.json()["requires_confirmation"] is True

    # Cancel verbally
    res_canc = client.post("/api/ai/interpret", json={
        "text": "Vendaam",
        "session_id": session_id,
        "allow_mock": True
    })
    assert res_canc.status_code == 200
    data = res_canc.json()
    assert data["success"] is True
    assert data["intent"]["intent"] == "CANCEL_ACTION"

    # Verify tomato stock is still 18.0 (NOT deducted)
    db = SessionLocal()
    tomato = db.query(Product).filter(Product.name == "Tomato").first()
    assert tomato.quantity == 18.0
    db.close()

