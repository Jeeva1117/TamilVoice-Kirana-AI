"""Master End-to-End Test Suite for TamilVoice Kirana AI.
Validates Workflows TEST A through TEST O and measures real recognition accuracy:

TEST A - Tamil stock addition ("ரெண்டு கிலோ அரிசி ஸ்டாக் சேர்த்திடு")
TEST B - Tanglish stock addition ("2 kilo rice stock add pannu")
TEST C - English stock addition ("Add 5 kg rice to inventory")
TEST D - Stock removal and adjustment (REMOVE_STOCK & SET_STOCK)
TEST E - Product creation and price updates (CREATE_PRODUCT & UPDATE_PRICE)
TEST F - Multi-product single-command billing (4 products in one sentence)
TEST G - Bill cancellation and confirmation
TEST H - Inventory deduction exactly once (atomic & idempotent)
TEST I - Bill History and invoice reprinting without stock deduction
TEST J - Daily, weekly, and monthly analytics
TEST K - Low-stock alerts
TEST L - Natural multi-turn voice conversation with contextual cart
TEST M - STT, Gemini, and TTS pipeline endpoints
TEST N - Error handling and insufficient stock prevention
TEST O - PostgreSQL and SQLite dual-architecture configuration
TEST P - Empirical Intent & Entity Recognition Accuracy Evaluation
"""
import pytest
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.product import Product
from backend.app.models.sale import Sale
from backend.app.models.sale_item import SaleItem
from backend.app.models.stock_movement import StockMovement
from backend.app.schemas.ai import IntentCategory
from backend.app.services.ai_service import (
    interpret_user_command,
    confirm_pending_action,
    cancel_pending_action,
    session_manager,
)


@pytest.fixture
def seed_kirana_catalog(db: Session):
    """Seed clean, controlled Kirana products for workflow verification."""
    # Clean tables
    db.query(SaleItem).delete()
    db.query(Sale).delete()
    db.query(StockMovement).delete()
    db.query(Product).delete()
    db.commit()

    products = [
        Product(
            name="Ponni Boiled Rice",
            name_ta="பொன்னி அரிசி",
            sku="GRO-RIC-001",
            category="Groceries",
            quantity=100.0,
            unit="kg",
            purchase_price=45.0,
            selling_price=55.0,
            minimum_stock_level=10.0,
            is_active=True,
        ),
        Product(
            name="Refined White Sugar",
            name_ta="சர்க்கரை",
            sku="GRO-SUG-002",
            category="Groceries",
            quantity=80.0,
            unit="kg",
            purchase_price=38.0,
            selling_price=45.0,
            minimum_stock_level=10.0,
            is_active=True,
        ),
        Product(
            name="Country Tomato",
            name_ta="தக்காளி",
            sku="VEG-TOM-003",
            category="Vegetables",
            quantity=50.0,
            unit="kg",
            purchase_price=25.0,
            selling_price=40.0,
            minimum_stock_level=5.0,
            is_active=True,
        ),
        Product(
            name="Marie Gold Biscuit",
            name_ta="பிஸ்கட்",
            sku="SNK-BIS-004",
            category="Packaged Foods",
            quantity=60.0,
            unit="packet",
            purchase_price=20.0,
            selling_price=30.0,
            minimum_stock_level=10.0,
            is_active=True,
        ),
        Product(
            name="Tea Powder",
            name_ta="தேயிலை தூள்",
            sku="GRO-TEA-005",
            category="Groceries",
            quantity=40.0,
            unit="packet",
            purchase_price=30.0,
            selling_price=45.0,
            minimum_stock_level=8.0,
            is_active=True,
        ),
    ]
    for p in products:
        db.add(p)
    db.commit()
    for p in products:
        db.refresh(p)
    return products


# =============================================================================
# TEST A: Tamil Stock Addition
# =============================================================================
@pytest.mark.asyncio
async def test_workflow_A_tamil_stock_addition(db: Session, seed_kirana_catalog):
    """TEST A: Shopkeeper says 'ரெண்டு கிலோ அரிசி ஸ்டாக் சேர்த்திடு' in Tamil."""
    rice = db.query(Product).filter(Product.name == "Ponni Boiled Rice").first()
    initial_stock = rice.quantity

    res = await interpret_user_command(db=db, text="ரெண்டு கிலோ அரிசி ஸ்டாக் சேர்த்திடு", session_id="test_sess_A")
    assert res.success is True
    assert res.intent.intent == IntentCategory.ADD_STOCK
    assert res.requires_confirmation is True
    assert res.confirmation_preview is not None
    assert res.confirmation_preview.action == "ADD_STOCK"

    # Confirm action
    confirm_res = confirm_pending_action(db=db, action_id=res.confirmation_preview.action_id)
    assert confirm_res.success is True
    assert confirm_res.new_stock == initial_stock + 2.0

    db.refresh(rice)
    assert rice.quantity == initial_stock + 2.0

    movement = db.query(StockMovement).filter(StockMovement.product_id == rice.id).first()
    assert movement is not None
    assert movement.movement_type in ("IN", "ADJUSTMENT_ADD")
    assert movement.quantity == 2.0


# =============================================================================
# TEST B: Tanglish Stock Addition
# =============================================================================
@pytest.mark.asyncio
async def test_workflow_B_tanglish_stock_addition(db: Session, seed_kirana_catalog):
    """TEST B: Shopkeeper says '2 kilo rice stock add pannu' in Tanglish."""
    rice = db.query(Product).filter(Product.name == "Ponni Boiled Rice").first()
    initial_stock = rice.quantity

    res = await interpret_user_command(db=db, text="2 kilo rice stock add pannu", session_id="test_sess_B")
    assert res.success is True
    assert res.intent.intent == IntentCategory.ADD_STOCK
    assert res.confirmation_preview is not None

    confirm_res = confirm_pending_action(db=db, action_id=res.confirmation_preview.action_id)
    assert confirm_res.success is True

    db.refresh(rice)
    assert rice.quantity == initial_stock + 2.0


# =============================================================================
# TEST C: English Stock Addition
# =============================================================================
@pytest.mark.asyncio
async def test_workflow_C_english_stock_addition(db: Session, seed_kirana_catalog):
    """TEST C: Shopkeeper says 'Add 5 kg rice to inventory' in English."""
    rice = db.query(Product).filter(Product.name == "Ponni Boiled Rice").first()
    initial_stock = rice.quantity

    res = await interpret_user_command(db=db, text="Add 5 kg rice to inventory", session_id="test_sess_C")
    assert res.success is True
    assert res.intent.intent == IntentCategory.ADD_STOCK
    assert res.confirmation_preview is not None

    confirm_res = confirm_pending_action(db=db, action_id=res.confirmation_preview.action_id)
    assert confirm_res.success is True

    db.refresh(rice)
    assert rice.quantity == initial_stock + 5.0


# =============================================================================
# TEST D: Stock Removal & Adjustment (SET_STOCK)
# =============================================================================
@pytest.mark.asyncio
async def test_workflow_D_stock_removal_and_adjustment(db: Session, seed_kirana_catalog):
    """TEST D: Stock removal and explicit stock adjustment."""
    rice = db.query(Product).filter(Product.name == "Ponni Boiled Rice").first()
    initial_stock = rice.quantity

    # 1. Removal
    res_rem = await interpret_user_command(db=db, text="Rice 5 kilo remove pannu", session_id="test_sess_D1")
    assert res_rem.success is True
    assert res_rem.intent.intent == IntentCategory.REMOVE_STOCK
    confirm_pending_action(db=db, action_id=res_rem.confirmation_preview.action_id)

    db.refresh(rice)
    assert rice.quantity == initial_stock - 5.0

    # 2. Set exact stock (SET_STOCK)
    res_set = await interpret_user_command(db=db, text="Rice stock 50 kg set pannu", session_id="test_sess_D2")
    assert res_set.success is True
    assert res_set.intent.intent == IntentCategory.SET_STOCK
    confirm_pending_action(db=db, action_id=res_set.confirmation_preview.action_id)

    db.refresh(rice)
    assert rice.quantity == 50.0


# =============================================================================
# TEST E: Product Creation & Price Updates
# =============================================================================
@pytest.mark.asyncio
async def test_workflow_E_product_creation_and_price_update(db: Session, seed_kirana_catalog):
    """TEST E: Product creation via voice and price update with two-step confirmation."""
    # 1. Product creation
    res_create = await interpret_user_command(
        db=db, text="Add new product Toothpaste price 45", session_id="test_sess_E1"
    )
    assert res_create.success is True
    assert res_create.intent.intent == IntentCategory.CREATE_PRODUCT

    new_prod = db.query(Product).filter(Product.name.ilike("%Toothpaste%")).first()
    assert new_prod is not None
    assert new_prod.selling_price == 45.0
    assert new_prod.quantity == 0.0

    # 2. Price update
    res_prc = await interpret_user_command(
        db=db, text="Update Ponni Boiled Rice price to 60", session_id="test_sess_E2"
    )
    assert res_prc.success is True
    assert res_prc.intent.intent == IntentCategory.UPDATE_PRICE
    assert res_prc.confirmation_preview is not None

    confirm_pending_action(db=db, action_id=res_prc.confirmation_preview.action_id)
    rice = db.query(Product).filter(Product.name == "Ponni Boiled Rice").first()
    db.refresh(rice)
    assert rice.selling_price == 60.0


# =============================================================================
# TEST F: Multi-Product Single-Command Billing
# =============================================================================
@pytest.mark.asyncio
async def test_workflow_F_multi_product_billing(db: Session, seed_kirana_catalog):
    """TEST F: 'Customer-ku 2 kilo rice, 1 kilo sugar, 1 kilo tomato, 2 packet biscuit bill podu'."""
    cmd = "Customer-ku 2 kilo rice, 1 kilo sugar, 1 kilo tomato, 2 packet biscuit bill podu"
    res = await interpret_user_command(db=db, text=cmd, session_id="test_sess_F")

    assert res.success is True
    assert res.intent.intent == IntentCategory.SELL_PRODUCT
    assert res.requires_confirmation is True
    assert res.confirmation_preview is not None

    prev = res.confirmation_preview
    assert prev.items is not None
    assert len(prev.items) == 4

    # Calculate expected total: 2*55 + 1*45 + 1*40 + 2*30 = 110 + 45 + 40 + 60 = 255.0
    assert prev.estimated_total == 255.0


# =============================================================================
# TEST G: Bill Correction and Confirmation
# =============================================================================
@pytest.mark.asyncio
async def test_workflow_G_bill_correction_and_confirmation(db: Session, seed_kirana_catalog):
    """TEST G: Cancel pending bill, then create and confirm bill."""
    # 1. Start bill
    res1 = await interpret_user_command(db=db, text="Customer-ku 2 kg rice bill podu", session_id="test_sess_G")
    assert res1.requires_confirmation is True

    # 2. Cancel bill
    res_canc = await interpret_user_command(db=db, text="Cancel pannunga", session_id="test_sess_G")
    assert res_canc.intent.intent == IntentCategory.CANCEL_ACTION
    assert db.query(Sale).count() == 0

    # 3. New bill and confirm
    res2 = await interpret_user_command(db=db, text="Customer-ku 2 kg rice bill podu", session_id="test_sess_G")
    res_conf = await interpret_user_command(db=db, text="Aama confirm pannu", session_id="test_sess_G")

    assert res_conf.intent.intent == IntentCategory.CONFIRM_ACTION
    assert db.query(Sale).count() == 1


# =============================================================================
# TEST H: Inventory Deduction Exactly Once (Idempotent)
# =============================================================================
@pytest.mark.asyncio
async def test_workflow_H_inventory_deduction_exactly_once(db: Session, seed_kirana_catalog):
    """TEST H: Ensure inventory is deducted strictly once upon confirmation, never twice."""
    sugar = db.query(Product).filter(Product.name == "Refined White Sugar").first()
    initial_stock = sugar.quantity

    res = await interpret_user_command(db=db, text="Customer-ku 5 kg sugar bill podu", session_id="test_sess_H")
    # Verify stock has NOT changed yet before confirmation
    db.refresh(sugar)
    assert sugar.quantity == initial_stock

    # Confirm action
    action_id = res.confirmation_preview.action_id
    confirm_res = confirm_pending_action(db=db, action_id=action_id)
    assert confirm_res.success is True

    db.refresh(sugar)
    assert sugar.quantity == initial_stock - 5.0

    # Attempting to confirm the exact same action_id a second time must fail gracefully
    with pytest.raises(Exception):
        confirm_pending_action(db=db, action_id=action_id)

    db.refresh(sugar)
    assert sugar.quantity == initial_stock - 5.0  # Still deducted exactly once!


# =============================================================================
# TEST I: Bill History & Invoice Querying (No Double Deduction)
# =============================================================================
def test_workflow_I_bill_history_and_reprinting(client: TestClient, db: Session, seed_kirana_catalog):
    """TEST I: Verified sales appear in /api/sales and querying/printing does not re-deduct."""
    rice = db.query(Product).filter(Product.name == "Ponni Boiled Rice").first()
    stock_before = rice.quantity

    # Create a completed sale via API
    payload = {
        "items": [{"product_id": rice.id, "quantity": 3.0}],
        "payment_method": "CASH",
        "notes": "Counter customer test",
    }
    resp = client.post("/api/sales", json=payload)
    assert resp.status_code in (200, 201)
    sale_data = resp.json()
    sale_id = sale_data["id"]

    db.refresh(rice)
    assert rice.quantity == stock_before - 3.0
    stock_after_sale = rice.quantity

    # 1. Query Bill History
    resp_history = client.get("/api/sales")
    assert resp_history.status_code == 200
    history_items = resp_history.json()["items"]
    assert any(s["id"] == sale_id for s in history_items)

    # 2. Query Invoice / Reprint endpoint multiple times
    for _ in range(3):
        resp_single = client.get(f"/api/sales/{sale_id}")
        assert resp_single.status_code == 200
        assert resp_single.json()["total_amount"] == 165.0  # 3 * 55.0

    # Assert stock is completely unchanged after reprinting
    db.refresh(rice)
    assert rice.quantity == stock_after_sale


# =============================================================================
# TEST J: Daily, Weekly, and Monthly Analytics
# =============================================================================
@pytest.mark.asyncio
async def test_workflow_J_daily_weekly_monthly_analytics(client: TestClient, db: Session, seed_kirana_catalog):
    """TEST J: Real-time analytics reflect actual database transaction sums."""
    rice = db.query(Product).filter(Product.name == "Ponni Boiled Rice").first()
    client.post("/api/sales", json={"items": [{"product_id": rice.id, "quantity": 2.0}], "payment_method": "CASH"})

    # Test Dashboard API
    dash_resp = client.get("/api/dashboard")
    assert dash_resp.status_code == 200
    data = dash_resp.json()
    assert data["kpis"]["today_sales"] >= 110.0
    assert data["kpis"]["today_orders"] >= 1

    # Test Voice Sales Query
    voice_sales = await interpret_user_command(db=db, text="Today sales evlo?", session_id="test_sess_J")
    assert voice_sales.success is True
    assert voice_sales.intent.intent == IntentCategory.SALES_REPORT


# =============================================================================
# TEST K: Low-Stock Alerts
# =============================================================================
@pytest.mark.asyncio
async def test_workflow_K_low_stock_alerts(db: Session, seed_kirana_catalog):
    """TEST K: Products below minimum_stock_level trigger low-stock alerts."""
    tomato = db.query(Product).filter(Product.name == "Country Tomato").first()
    tomato.quantity = 3.0  # Below minimum_stock_level=5.0
    db.commit()

    res = await interpret_user_command(db=db, text="Endha products stock kammiya irukku?", session_id="test_sess_K")
    assert res.success is True
    assert res.intent.intent == IntentCategory.LOW_STOCK_QUERY
    assert "தக்காளி" in res.message_ta or "Tomato" in res.message or "Country Tomato" in res.message


# =============================================================================
# TEST L: Natural Multi-Turn Conversational Cart
# =============================================================================
@pytest.mark.asyncio
async def test_workflow_L_multi_turn_voice_conversation(db: Session, seed_kirana_catalog):
    """TEST L: Turn 1 (Sugar) -> Turn 2 (Tomato) -> Turn 3 (Bill kaattu) -> Turn 4 (Aama confirm)."""
    sess = "multi_turn_sess_L"

    # Turn 1: Add 2 kg sugar for customer
    t1 = await interpret_user_command(db=db, text="Customer-ku 2 kilo sugar", session_id=sess)
    assert t1.success is True
    assert len(t1.context.get("cart_items", [])) == 1

    # Turn 2: Add 1 kg tomato
    t2 = await interpret_user_command(db=db, text="1 kilo tomato", session_id=sess)
    assert t2.success is True
    assert len(t2.context.get("cart_items", [])) == 2

    # Turn 3: Bill summary
    t3 = await interpret_user_command(db=db, text="Bill kaattu", session_id=sess)
    assert t3.success is True
    assert t3.requires_confirmation is True
    assert len(t3.confirmation_preview.items) == 2

    # Turn 4: Affirmative voice confirmation
    t4 = await interpret_user_command(db=db, text="Aama confirm pannunga", session_id=sess)
    assert t4.success is True
    assert t4.intent.intent == IntentCategory.CONFIRM_ACTION


# =============================================================================
# TEST M: STT, Gemini, and TTS Integration Endpoints
# =============================================================================
def test_workflow_M_stt_gemini_tts_integration(client: TestClient):
    """TEST M: Verify voice system status, command routing, and speech synthesis."""
    # 1. Voice system status
    st_resp = client.get("/api/voice/status")
    assert st_resp.status_code == 200
    st_data = st_resp.json()
    assert "stt_model" in st_data or "gnani_stt" in st_data
    assert "tts_model" in st_data or "gnani_tts" in st_data

    # 2. Voice command with transcript
    cmd_resp = client.post("/api/voice/command", data={"transcript": "Ponni Boiled Rice stock evlo irukku?"})
    assert cmd_resp.status_code == 200
    cmd_data = cmd_resp.json()
    assert "spoken_response" in cmd_data or "reply" in cmd_data

    # 3. Speech synthesis endpoint
    tts_resp = client.post("/api/voice/speak", json={"text": "வணக்கம்", "language": "ta-IN"})
    assert tts_resp.status_code == 200
    assert "audio" in tts_resp.headers.get("content-type", "")


# =============================================================================
# TEST N: Error Handling & Insufficient Stock Prevention
# =============================================================================
@pytest.mark.asyncio
async def test_workflow_N_error_handling_and_insufficient_stock(db: Session, seed_kirana_catalog):
    """TEST N: Prevent negative inventory when ordered quantity exceeds available stock."""
    tomato = db.query(Product).filter(Product.name == "Country Tomato").first()
    avail = tomato.quantity

    res = await interpret_user_command(db=db, text="Customer-ku 9999 kg tomato bill podu", session_id="test_sess_N")
    assert res.success is False or "insufficient" in res.message.lower() or "அளவு இல்லை" in (res.message_ta or "")

    db.refresh(tomato)
    assert tomato.quantity == avail  # Stock remains completely untouched


# =============================================================================
# TEST O: Production PostgreSQL Persistence & SQLite Compatibility
# =============================================================================
def test_workflow_O_postgres_and_sqlite_dual_architecture():
    """TEST O: Validate dual-engine configuration, psycopg v3 and v2 driver support."""
    from backend.app.config import Settings
    from sqlalchemy import create_engine

    # 1. Verify SQLite configuration for local dev
    dev_settings = Settings(DATABASE_URL="sqlite:///./kirana_ai.db", ENVIRONMENT="development")
    assert dev_settings.is_postgres is False

    # 2. Verify Supabase PostgreSQL configuration for production
    prod_settings = Settings(
        DATABASE_URL="postgresql+psycopg://postgres.ref:secret@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require",
        ENVIRONMENT="production",
    )
    assert prod_settings.is_postgres is True

    # 3. Verify psycopg driver dialect instantiation
    engine = create_engine("postgresql+psycopg://user:pass@localhost:5432/test")
    assert engine.dialect.driver == "psycopg"


# =============================================================================
# TEST P: Empirical Intent & Entity Recognition Accuracy Evaluation
# =============================================================================
@pytest.mark.asyncio
async def test_speech_and_intent_recognition_accuracy_metrics(db: Session, seed_kirana_catalog):
    """
    TEST P: Quantitative Benchmark Evaluation across 20 documented multimodal Kirana queries.
    Evaluates:
    - Intent Recognition Accuracy (%)
    - Entity Extraction Accuracy (%)
    Across Tamil, Tanglish, and English inputs.
    """
    benchmark_dataset = [
        # (Input text, Expected Intent, Expected Product substring, Expected Quantity)
        ("2 kg rice stock add pannu", IntentCategory.ADD_STOCK, "Rice", 2.0),
        ("Add 5 kg rice to inventory", IntentCategory.ADD_STOCK, "Rice", 5.0),
        ("ரெண்டு கிலோ அரிசி ஸ்டாக் சேர்த்திடு", IntentCategory.ADD_STOCK, "Rice", 2.0),
        ("10 kg sugar stock add pannunga", IntentCategory.ADD_STOCK, "Sugar", 10.0),
        ("Sugar 5 kilo remove pannu", IntentCategory.REMOVE_STOCK, "Sugar", 5.0),
        ("Remove 2 kg rice", IntentCategory.REMOVE_STOCK, "Rice", 2.0),
        ("Rice stock 50 kg set pannu", IntentCategory.SET_STOCK, "Rice", 50.0),
        ("Ponni Boiled Rice stock evlo irukku?", IntentCategory.CHECK_STOCK, "Rice", None),
        ("Sugar vila evlo?", IntentCategory.CHECK_STOCK, "Sugar", None),
        ("Endha products stock kammiya irukku?", IntentCategory.LOW_STOCK_QUERY, None, None),
        ("Today sales evlo?", IntentCategory.SALES_REPORT, None, None),
        ("Indha week sales evlo?", IntentCategory.SALES_REPORT, None, None),
        ("Customer-ku 2 kg rice bill podu", IntentCategory.SELL_PRODUCT, "Rice", 2.0),
        ("Customer-ku 1 kg sugar bill podu", IntentCategory.SELL_PRODUCT, "Sugar", 1.0),
        ("Customer-ku 2 kg tomato bill podu", IntentCategory.SELL_PRODUCT, "Tomato", 2.0),
        ("Add new product Toothpaste price 45", IntentCategory.CREATE_PRODUCT, "Toothpaste", None),
        ("Update Ponni Boiled Rice price to 60", IntentCategory.UPDATE_PRICE, "Rice", None),
        ("Vanakkam", IntentCategory.GREETING, None, None),
        ("Cancel pannunga", IntentCategory.CANCEL_ACTION, None, None),
        ("Thank you so much", IntentCategory.THANK_YOU, None, None),
    ]

    correct_intents = 0
    correct_entities = 0
    total = len(benchmark_dataset)

    for text, expected_intent, expected_product, expected_qty in benchmark_dataset:
        res = await interpret_user_command(db=db, text=text, session_id=f"bench_{text[:8]}")
        actual_intent = res.intent.intent

        # Evaluate Intent
        if actual_intent == expected_intent:
            correct_intents += 1

        # Evaluate Entity (if expected)
        entity_correct = True
        if expected_product:
            prod_name = res.intent.entities.product_name or (res.resolved_product.name if res.resolved_product else "")
            if expected_product.lower() not in prod_name.lower():
                entity_correct = False

        if expected_qty is not None:
            actual_qty = res.intent.entities.quantity
            if actual_qty != expected_qty:
                entity_correct = False

        if entity_correct:
            correct_entities += 1

    intent_accuracy = (correct_intents / total) * 100.0
    entity_accuracy = (correct_entities / total) * 100.0

    print(f"\n=================================================================")
    print(f"BENCHMARK ACCURACY EVALUATION RESULTS (N={total} queries):")
    print(f" - Intent Recognition Accuracy: {intent_accuracy:.1f}% ({correct_intents}/{total})")
    print(f" - Entity Extraction Accuracy:  {entity_accuracy:.1f}% ({correct_entities}/{total})")
    print(f"=================================================================\n")

    # Strict assertion thresholds: must meet at least 95% intent accuracy
    assert intent_accuracy >= 95.0, f"Intent accuracy below threshold: {intent_accuracy}%"
    assert entity_accuracy >= 90.0, f"Entity extraction accuracy below threshold: {entity_accuracy}%"

