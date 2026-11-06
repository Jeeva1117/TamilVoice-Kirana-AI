"""Phase 5: Gemini AI Intent Extraction, Product Resolution, and Confirmation Tests."""
import json
import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status

from backend.app.config import settings
from backend.app.schemas.ai import (
    CommandIntent,
    IntentCategory,
    CommandEntities,
    InterpretResponse,
)
from backend.app.services.product_resolver import resolve_product, ResolutionStatus
from backend.app.services.gemini_client import (
    GeminiClient,
    GeminiError,
    GeminiNotConfiguredError,
)
from backend.app.services.ai_service import (
    PendingAction,
    pending_store,
)
from backend.app.models.product import Product


# =============================================================================
# 1. Intent Extraction & Pydantic Schema Validation Tests
# =============================================================================

def test_intent_schema_valid_tanglish_add_stock():
    """Verify Tanglish stock addition produces valid CommandIntent."""
    raw = {
        "intent": "ADD_STOCK",
        "language": "Tanglish",
        "original_text": "Innaiku 5 kilo rice stock add pannunga",
        "normalized_text": "Add 5 kilograms of rice to inventory",
        "entities": {
            "product_name": "rice",
            "quantity": 5.0,
            "unit": "kg",
            "date": "today"
        },
        "confidence": 0.96,
        "requires_clarification": False,
        "clarification_question": None
    }
    intent = CommandIntent(**raw)
    assert intent.intent == IntentCategory.ADD_STOCK
    assert intent.entities.quantity == 5.0
    assert intent.entities.unit == "kg"
    assert intent.requires_clarification is False


def test_intent_schema_missing_quantity_requires_clarification():
    """Ensure missing quantity automatically forces requires_clarification=True."""
    raw = {
        "intent": "ADD_STOCK",
        "language": "Tanglish",
        "original_text": "Rice stock add pannunga",
        "normalized_text": "Add rice stock",
        "entities": {
            "product_name": "rice",
            "quantity": None,
            "unit": None
        },
        "confidence": 0.85,
        "requires_clarification": False,  # Should be forced to True by validator
        "clarification_question": None
    }
    intent = CommandIntent(**raw)
    assert intent.requires_clarification is True
    assert "How much rice" in intent.clarification_question


def test_intent_schema_missing_product_requires_clarification():
    """Ensure missing product name automatically forces requires_clarification=True."""
    raw = {
        "intent": "SELL_PRODUCT",
        "language": "English",
        "original_text": "Sell 2 packets to customer",
        "normalized_text": "Sell 2 packets",
        "entities": {
            "product_name": None,
            "quantity": 2.0,
            "unit": "packet"
        },
        "confidence": 0.88,
        "requires_clarification": False,
        "clarification_question": None
    }
    intent = CommandIntent(**raw)
    assert intent.requires_clarification is True
    assert "Which product" in intent.clarification_question


def test_intent_schema_unit_normalization():
    """Verify colloquial unit strings normalize to standard Kirana units."""
    entities = CommandEntities(product_name="sugar", quantity=3.0, unit="kilos")
    assert entities.unit == "kg"

    entities_oil = CommandEntities(product_name="oil", quantity=2.0, unit="litres")
    assert entities_oil.unit == "litre"

    entities_pkt = CommandEntities(product_name="biscuit", quantity=5.0, unit="packets")
    assert entities_pkt.unit == "packet"


def test_intent_schema_rejects_negative_quantity():
    """Verify negative quantity raises Pydantic validation error."""
    with pytest.raises(ValueError):
        CommandEntities(product_name="rice", quantity=-5.0)


# =============================================================================
# 2. Product Catalog Resolution Tests
# =============================================================================

def test_resolve_exact_product(db, sample_product):
    """Test exact match by name and SKU."""
    status_res, prod, candidates = resolve_product(db, "Ponni Boiled Rice")
    assert status_res == ResolutionStatus.MATCH
    assert prod.id == sample_product.id

    status_sku, prod_sku, _ = resolve_product(db, sample_product.sku)
    assert status_sku == ResolutionStatus.MATCH
    assert prod_sku.id == sample_product.id


def test_resolve_tamil_synonym(db, sample_product):
    """Test Tamil synonym 'அரிசி' maps to Ponni Boiled Rice."""
    status_res, prod, _ = resolve_product(db, "அரிசி")
    assert status_res == ResolutionStatus.MATCH
    assert prod.id == sample_product.id


def test_resolve_tanglish_synonym(db, sample_product):
    """Test Tanglish 'arisi' maps to Ponni Boiled Rice."""
    status_res, prod, _ = resolve_product(db, "arisi")
    assert status_res == ResolutionStatus.MATCH
    assert prod.id == sample_product.id


def test_resolve_multiple_matches_for_generic_term(db):
    """Test generic term 'dal' or 'paruppu' returns multiple matches when multiple dals exist."""
    toor = Product(
        name="Toor Dal First Quality",
        name_ta="துவரம் பருப்பு",
        sku="DAL-TOO-002",
        category="Dal & Pulses",
        quantity=30.0,
        unit="kg",
        purchase_price=130.0,
        selling_price=150.0,
        is_active=True,
    )
    urad = Product(
        name="Urad Dal White Whole",
        name_ta="உளுத்தம் பருப்பு",
        sku="DAL-URD-012",
        category="Dal & Pulses",
        quantity=20.0,
        unit="kg",
        purchase_price=120.0,
        selling_price=140.0,
        is_active=True,
    )
    db.add_all([toor, urad])
    db.commit()

    status_res, prod, candidates = resolve_product(db, "dal")
    assert status_res == ResolutionStatus.MULTIPLE_MATCHES
    assert len(candidates) == 2


def test_resolve_no_match_unknown_product(db):
    """Test searching for non-existent product returns NO_MATCH."""
    status_res, prod, candidates = resolve_product(db, "NonExistentItemXYZ")
    assert status_res == ResolutionStatus.NO_MATCH
    assert prod is None


# =============================================================================
# 3. AI Endpoints Integration Tests (Mocked Gemini)
# =============================================================================

def test_get_ai_status(client):
    """Test /api/ai/status returns status structure without leaking secrets."""
    response = client.get("/api/ai/status")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "configured" in data
    assert "enabled" in data
    assert "model" in data
    assert data["provider"] == "Google Gemini"
    assert "api_key" not in data  # Never expose credentials


@pytest.mark.asyncio
async def test_interpret_add_stock_endpoint(client, sample_product):
    """Test /api/ai/interpret for stock addition creates a confirmation preview."""
    mocked_intent = CommandIntent(
        intent=IntentCategory.ADD_STOCK,
        language="Tanglish",
        original_text="Innaiku 5 kilo rice stock add pannunga",
        normalized_text="Add 5 kg rice to inventory",
        entities=CommandEntities(product_name="rice", quantity=5.0, unit="kg"),
        confidence=0.98,
        requires_clarification=False
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock_key_xyz"), patch.object(settings, "GEMINI_ENABLED", True):
        with patch("backend.app.services.gemini_client.gemini_client.generate_intent_async", AsyncMock(return_value=mocked_intent)):
            response = client.post("/api/ai/interpret", json={"text": "Innaiku 5 kilo rice stock add pannunga"})
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["success"] is True
            assert data["requires_confirmation"] is True
            preview = data["confirmation_preview"]
            assert preview["action"] == "ADD_STOCK"
            assert preview["product_name"] == sample_product.name
            assert preview["quantity"] == 5.0
            assert preview["current_stock"] == sample_product.quantity
            assert preview["projected_stock"] == sample_product.quantity + 5.0
            assert "action_id" in preview


@pytest.mark.asyncio
async def test_interpret_sell_product_overselling_prevention(client, db, sample_product):
    """Test that trying to sell more than available stock is rejected."""
    sample_product.quantity = 4.0
    db.commit()

    mocked_intent = CommandIntent(
        intent=IntentCategory.SELL_PRODUCT,
        language="Tamil",
        original_text="10 கிலோ அரிசி விற்பனை",
        normalized_text="Sell 10 kg of rice",
        entities=CommandEntities(product_name="rice", quantity=10.0, unit="kg"),
        confidence=0.97,
        requires_clarification=False
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock_key_xyz"), patch.object(settings, "GEMINI_ENABLED", True):
        with patch("backend.app.services.gemini_client.gemini_client.generate_intent_async", AsyncMock(return_value=mocked_intent)):
            response = client.post("/api/ai/interpret", json={"text": "10 கிலோ அரிசி விற்பனை"})
            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Overselling rejected
            assert data["success"] is False
            assert data["requires_confirmation"] is False
            assert "Insufficient stock" in data["message"]


@pytest.mark.asyncio
async def test_confirm_and_cancel_workflow(client, db, sample_product):
    """Test full cycle: Interpret -> Confirm -> DB mutation & verify duplicate execution prevention."""
    initial_stock = sample_product.quantity

    mocked_intent = CommandIntent(
        intent=IntentCategory.ADD_STOCK,
        language="Tanglish",
        original_text="10 kilo rice add pannu",
        normalized_text="Add 10 kg rice",
        entities=CommandEntities(product_name="rice", quantity=10.0, unit="kg"),
        confidence=0.99,
        requires_clarification=False
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock_key_xyz"), patch.object(settings, "GEMINI_ENABLED", True):
        with patch("backend.app.services.gemini_client.gemini_client.generate_intent_async", AsyncMock(return_value=mocked_intent)):
            # 1. Interpret
            resp = client.post("/api/ai/interpret", json={"text": "10 kilo rice add pannu"})
            assert resp.status_code == status.HTTP_200_OK
            action_id = resp.json()["confirmation_preview"]["action_id"]

            # 2. Confirm action
            confirm_resp = client.post("/api/ai/confirm", json={"action_id": action_id})
            assert confirm_resp.status_code == status.HTTP_200_OK
            res_data = confirm_resp.json()
            assert res_data["success"] is True
            assert res_data["new_stock"] == initial_stock + 10.0

            # Verify SQLite DB updated
            db.refresh(sample_product)
            assert sample_product.quantity == initial_stock + 10.0

            # 3. Duplicate confirmation attempt must fail (Replay attack guard)
            dup_resp = client.post("/api/ai/confirm", json={"action_id": action_id})
            assert dup_resp.status_code == status.HTTP_400_BAD_REQUEST
            assert "expired or action already executed" in dup_resp.json()["detail"]


@pytest.mark.asyncio
async def test_cancel_pending_action_leaves_db_unchanged(client, db, sample_product):
    """Test cancelling pending action leaves SQLite inventory completely untouched."""
    initial_stock = sample_product.quantity

    mocked_intent = CommandIntent(
        intent=IntentCategory.ADD_STOCK,
        language="English",
        original_text="Add 15 kg rice",
        normalized_text="Add 15 kg rice",
        entities=CommandEntities(product_name="rice", quantity=15.0, unit="kg"),
        confidence=0.99,
        requires_clarification=False
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock_key_xyz"), patch.object(settings, "GEMINI_ENABLED", True):
        with patch("backend.app.services.gemini_client.gemini_client.generate_intent_async", AsyncMock(return_value=mocked_intent)):
            # Interpret
            resp = client.post("/api/ai/interpret", json={"text": "Add 15 kg rice"})
            action_id = resp.json()["confirmation_preview"]["action_id"]

            # Cancel
            cancel_resp = client.post("/api/ai/cancel", json={"action_id": action_id})
            assert cancel_resp.status_code == status.HTTP_200_OK
            assert cancel_resp.json()["success"] is True

            # DB check: Stock unchanged
            db.refresh(sample_product)
            assert sample_product.quantity == initial_stock


@pytest.mark.asyncio
async def test_interpret_read_only_stock_query(client, sample_product):
    """Test CHECK_STOCK read-only intent returns stock info without confirmation preview."""
    mocked_intent = CommandIntent(
        intent=IntentCategory.CHECK_STOCK,
        language="Tanglish",
        original_text="Rice stock evlo irukku?",
        normalized_text="What is the current stock of rice?",
        entities=CommandEntities(product_name="rice"),
        confidence=0.97,
        requires_clarification=False
    )

    with patch.object(settings, "GEMINI_API_KEY", "mock_key_xyz"), patch.object(settings, "GEMINI_ENABLED", True):
        with patch("backend.app.services.gemini_client.gemini_client.generate_intent_async", AsyncMock(return_value=mocked_intent)):
            resp = client.post("/api/ai/interpret", json={"text": "Rice stock evlo irukku?"})
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert data["success"] is True
            assert data["requires_confirmation"] is False
            assert data["confirmation_preview"] is None
            assert f"{sample_product.quantity}" in data["message"]


def test_interpret_unconfigured_gemini_raises_503(client):
    """Verify that when Gemini is not configured, /api/ai/interpret returns 503."""
    with patch.object(settings, "GEMINI_API_KEY", ""):
        resp = client.post("/api/ai/interpret", json={"text": "Rice stock add pannunga"})
        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Gemini API is not configured" in resp.json()["detail"]
