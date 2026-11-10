"""Comprehensive Automated Test Suite for Tamil-First Natural Speech Understanding.
Verifies all 15 realistic Kirana shopkeeper Tamil/Tanglish utterances:
1. “இன்னைக்கு rice add பண்ணு”
2. “இன்னைக்கு tomato one kg add பண்ணு”
3. “Tomato one kg”
4. “மசாலா bill போடு”
5. “Five kg tea powder add பண்ணு”
6. “அந்த rice இன்னும் five kilo”
7. “அரிசி stock எவ்வளவு?”
8. “இன்னைக்கு sales எவ்வளவு?”
9. “தக்காளி stock இல்லையா?”
10. “இல்ல, onion சொன்னேன்”
11. “அரை கிலோ tomato add பண்ணு”
12. “ஆயிரம் கிலோ rice add பண்ணு”
13. “அதுக்கு bill போடு”
14. “ஆமா”
15. “வேண்டாம் cancel பண்ணு”
Plus:
- In-sentence quantity correction: “இரண்டு கிலோ… இல்ல மூணு கிலோ” -> 3.0
- Relative addition with pronoun: “அதுல இன்னும் ஒரு kilo சேரு”
"""
import pytest
import asyncio
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models.product import Product
from backend.app.schemas.ai import IntentCategory
from backend.app.services.ai_service import interpret_user_command, session_manager, pending_store
from backend.app.services.speech_normalizer import normalize_spoken_numbers, extract_effective_quantity


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def clean_session():
    sid = "test_tamil_session_123"
    conv = session_manager.get_or_create(session_id=sid)
    # Reset
    conv.active_product_id = None
    conv.active_product_name = None
    conv.active_product_unit = None
    conv.last_action = None
    conv.last_quantity = None
    conv.last_unit = None
    conv.pending_action_id = None
    conv.pending_action_type = None
    conv.pending_items = None
    conv.missing_field = None
    return sid


@pytest.mark.asyncio
async def test_01_missing_quantity_rice_add(db, clean_session):
    """Utterance 1: “இன்னைக்கு rice add பண்ணு” -> Intent: ADD_STOCK, Qty missing -> Tamil clarification."""
    res = await interpret_user_command(db=db, text="இன்னைக்கு rice add பண்ணு", allow_mock=True, session_id=clean_session)
    assert res.success is True
    assert res.intent.intent == IntentCategory.ADD_STOCK
    assert "Rice" in (res.intent.entities.product_name or "")
    assert res.intent.entities.quantity is None
    assert res.intent.requires_clarification is True
    # Must NOT say "I could not understand"
    assert "could not understand" not in res.message_ta.lower()
    assert "அரிசி" in res.message_ta and "சேர்க்க" in res.message_ta


@pytest.mark.asyncio
async def test_02_tomato_add_with_quantity(db, clean_session):
    """Utterance 2: “இன்னைக்கு tomato one kg add பண்ணு” -> ADD_STOCK, Tomato, 1 kg -> Needs confirmation."""
    res = await interpret_user_command(db=db, text="இன்னைக்கு tomato one kg add பண்ணு", allow_mock=True, session_id=clean_session)
    assert res.success is True
    assert res.intent.intent == IntentCategory.ADD_STOCK
    assert res.intent.entities.quantity == 1.0
    assert res.requires_confirmation is True
    assert res.confirmation_preview is not None
    assert "தக்காளி" in res.message_ta
    assert "could not understand" not in res.message_ta.lower()


@pytest.mark.asyncio
async def test_03_fragmented_retail_sale_tomato(db, clean_session):
    """Utterance 3: “Tomato one kg” -> Retail customer sale (SELL_PRODUCT) -> 1 kg Tomato."""
    res = await interpret_user_command(db=db, text="Tomato one kg", allow_mock=True, session_id=clean_session)
    assert res.success is True
    assert res.intent.intent == IntentCategory.SELL_PRODUCT
    assert res.intent.entities.quantity == 1.0
    assert "Tomato" in res.intent.entities.product_name
    assert res.requires_confirmation is True
    assert res.confirmation_preview is not None
    assert "தக்காளி" in res.message_ta or "Tomato" in res.message_ta


@pytest.mark.asyncio
async def test_04_masala_bill_missing_quantity(db, clean_session):
    """Utterance 4: “மசாலா bill போடு” -> SELL_PRODUCT, Masala, quantity missing -> Ask in Tamil."""
    res = await interpret_user_command(db=db, text="மசாலா bill போடு", allow_mock=True, session_id=clean_session)
    assert res.success is True
    assert res.intent.intent == IntentCategory.SELL_PRODUCT
    assert res.intent.requires_clarification is True
    assert "could not understand" not in res.message_ta.lower()
    assert "மசாலா" in res.message_ta and "எவ்வளவு" in res.message_ta


@pytest.mark.asyncio
async def test_05_tea_powder_stock_add(db, clean_session):
    """Utterance 5: “Five kg tea powder add பண்ணு” -> ADD_STOCK, Tea Powder, 5 kg -> Needs confirmation."""
    res = await interpret_user_command(db=db, text="Five kg tea powder add பண்ணு", allow_mock=True, session_id=clean_session)
    assert res.success is True
    assert res.intent.intent == IntentCategory.ADD_STOCK
    assert res.intent.entities.quantity == 5.0
    assert "Tea" in res.intent.entities.product_name
    assert res.requires_confirmation is True


@pytest.mark.asyncio
async def test_06_contextual_relative_addition(db, clean_session):
    """Utterance 6: “அந்த rice இன்னும் five kilo” -> Contextual ADD_STOCK -> 5 kg added to rice."""
    # First establish context with rice
    await interpret_user_command(db=db, text="Rice stock எவ்வளவு?", allow_mock=True, session_id=clean_session)
    # Now follow-up with relative addition
    res = await interpret_user_command(db=db, text="அந்த rice இன்னும் five kilo", allow_mock=True, session_id=clean_session)
    assert res.success is True
    assert res.intent.intent == IntentCategory.ADD_STOCK
    assert res.intent.entities.quantity == 5.0
    assert "Rice" in (res.resolved_product.name if res.resolved_product else res.intent.entities.product_name)


@pytest.mark.asyncio
async def test_07_rice_stock_inquiry(db, clean_session):
    """Utterance 7: “அரிசி stock எவ்வளவு?” -> CHECK_STOCK -> Returns actual DB quantity in Tamil."""
    rice = db.query(Product).filter(Product.id == 1).first()
    res = await interpret_user_command(db=db, text="அரிசி stock எவ்வளவு?", allow_mock=True, session_id=clean_session)
    assert res.success is True
    assert res.intent.intent == IntentCategory.CHECK_STOCK
    assert "அரிசி" in res.message_ta or "Rice" in res.message_ta
    assert "தற்போது" in res.message_ta or "உள்ளது" in res.message_ta
    assert str(int(rice.quantity)) in res.message_ta or f"{rice.quantity:.0f}" in res.message_ta


@pytest.mark.asyncio
async def test_08_sales_report_today(db, clean_session):
    """Utterance 8: “இன்னைக்கு sales எவ்வளவு?” -> SALES_REPORT -> Returns today sales total in Tamil."""
    res = await interpret_user_command(db=db, text="இன்னைக்கு sales எவ்வளவு?", allow_mock=True, session_id=clean_session)
    assert res.success is True
    assert res.intent.intent == IntentCategory.SALES_REPORT
    assert "விற்பனை" in res.message_ta
    assert "could not understand" not in res.message_ta.lower()


@pytest.mark.asyncio
async def test_09_tomato_stock_availability_check(db, clean_session):
    """Utterance 9: “தக்காளி stock இல்லையா?” -> CHECK_STOCK -> Confirms stock availability in Tamil."""
    res = await interpret_user_command(db=db, text="தக்காளி stock இல்லையா?", allow_mock=True, session_id=clean_session)
    assert res.success is True
    assert res.intent.intent == IntentCategory.CHECK_STOCK
    assert "தக்காளி" in res.message_ta
    assert "stock உள்ளது" in res.message_ta


@pytest.mark.asyncio
async def test_10_product_correction_turn(db, clean_session):
    """Utterance 10: “இல்ல, onion சொன்னேன்” -> Corrects previous product to Onion."""
    # First turn: User talks about tomato
    await interpret_user_command(db=db, text="தக்காளி 1 kg சேர்க்கிறேன்", allow_mock=True, session_id=clean_session)
    # Correction turn: "No, I said Onion!"
    res = await interpret_user_command(db=db, text="இல்ல, onion சொன்னேன்", allow_mock=True, session_id=clean_session)
    assert res.success is True
    assert res.context.get("active_product_name") == "Onion"
    assert "வெங்காயம்" in res.message_ta or "Onion" in res.message_ta


@pytest.mark.asyncio
async def test_11_fractional_quantity_arai_kilo(db, clean_session):
    """Utterance 11: “அரை கிலோ tomato add பண்ணு” -> 0.5 kg Tomato."""
    res = await interpret_user_command(db=db, text="அரை கிலோ tomato add பண்ணு", allow_mock=True, session_id=clean_session)
    assert res.success is True
    assert res.intent.intent == IntentCategory.ADD_STOCK
    assert res.intent.entities.quantity == 0.5
    assert res.requires_confirmation is True


@pytest.mark.asyncio
async def test_12_large_quantity_alert(db, clean_session):
    """Utterance 12: “ஆயிரம் கிலோ rice add பண்ணு” -> 1000 kg Rice with large stock alert."""
    res = await interpret_user_command(db=db, text="ஆயிரம் கிலோ rice add பண்ணு", allow_mock=True, session_id=clean_session)
    assert res.success is True
    assert res.intent.intent == IntentCategory.ADD_STOCK
    assert res.intent.entities.quantity == 1000.0
    assert "கவனிக்க: பெரிய அளவு!" in res.message_ta
    assert "1000" in res.message_ta


@pytest.mark.asyncio
async def test_13_pronoun_reference_bill(db, clean_session):
    """Utterance 13: “அதுக்கு bill போடு” -> Uses active product in context for SELL_PRODUCT."""
    # Step A: Establish active product
    await interpret_user_command(db=db, text="Onion stock எவ்வளவு?", allow_mock=True, session_id=clean_session)
    # Step B: "Adhuku bill podu"
    res = await interpret_user_command(db=db, text="அதுக்கு bill போடு", allow_mock=True, session_id=clean_session)
    assert res.success is True
    assert res.intent.intent == IntentCategory.SELL_PRODUCT
    assert "Onion" in (res.intent.entities.product_name or res.context.get("active_product_name"))


@pytest.mark.asyncio
async def test_14_affirmative_voice_confirmation(db, clean_session):
    """Utterance 14: “ஆமா” -> CONFIRM_ACTION commits transaction to DB."""
    # Step A: Create confirmation preview for 2 kg Tomato
    init_res = await interpret_user_command(db=db, text="Tomato 2 kg add பண்ணு", allow_mock=True, session_id=clean_session)
    assert init_res.requires_confirmation is True
    # Step B: Speak "ஆமா"
    confirm_res = await interpret_user_command(db=db, text="ஆமா", allow_mock=True, session_id=clean_session)
    assert confirm_res.success is True
    assert confirm_res.intent.intent == IntentCategory.CONFIRM_ACTION
    assert "சேர்க்கப்பட்டது" in confirm_res.message_ta or "மொத்தம்" in confirm_res.message_ta


@pytest.mark.asyncio
async def test_15_cancellation_action(db, clean_session):
    """Utterance 15: “வேண்டாம் cancel பண்ணு” -> CANCEL_ACTION safely drops pending action."""
    # Step A: Create confirmation preview
    init_res = await interpret_user_command(db=db, text="Tomato 2 kg add பண்ணு", allow_mock=True, session_id=clean_session)
    assert init_res.requires_confirmation is True
    # Step B: Speak cancellation
    cancel_res = await interpret_user_command(db=db, text="வேண்டாம் cancel பண்ணு", allow_mock=True, session_id=clean_session)
    assert cancel_res.success is True
    assert cancel_res.intent.intent == IntentCategory.CANCEL_ACTION
    assert "ரத்து செய்யப்பட்டது" in cancel_res.message_ta


@pytest.mark.asyncio
async def test_in_sentence_quantity_correction(db, clean_session):
    """Extra: “இரண்டு கிலோ… இல்ல மூணு கிலோ” -> Correction in sentence resolves to 3.0."""
    eff = extract_effective_quantity("இரண்டு கிலோ… இல்ல மூணு கிலோ")
    assert eff == 3.0
    res = await interpret_user_command(db=db, text="இரண்டு கிலோ… இல்ல மூணு கிலோ tomato add பண்ணு", allow_mock=True, session_id=clean_session)
    assert res.intent.entities.quantity == 3.0

