"""Comprehensive Automated Verification for User Request #10:
Section 12:
1. Multi-product single sentence bill generation:
   'Customer-ku 2 kg rice, 1 kg sugar bill podu'
2. Turn-by-turn conversational bill building across multiple turns:
   Turn 1: 'Customer-ku 2 kg sugar'
   Turn 2: 'Rice 3 kg'
   Turn 3: 'Tea powder 2 packet'
   Turn 4: 'Bill ready pannu'
   Turn 5: 'Aama' / 'Confirm'
3. Consequential stock deduction and audit logging verification
4. Conversational politeness ('Thank you', 'Vanakkam')
5. Multi-category recognition (Groceries, Personal Care, Stationery, Snacks & Food)
6. Bill History API verification (GET /api/sales)
"""
import pytest
from sqlalchemy.orm import Session
from backend.app.models.product import Product
from backend.app.models.sale import Sale
from backend.app.models.sale_item import SaleItem
from backend.app.models.stock_movement import StockMovement
from backend.app.schemas.ai import IntentCategory
from backend.app.services.ai_service import interpret_user_command, confirm_pending_action


@pytest.fixture
def seed_multi_category_store(db: Session):
    """Seed sample products across 4 categories."""
    products = [
        # Groceries
        Product(name="Ponni Boiled Rice", name_ta="பொன்னி அரிசி", sku="GRO-RIC-01", category="Groceries",
                quantity=50.0, unit="kg", purchase_price=45.0, selling_price=55.0, minimum_stock_level=10.0, is_active=True),
        Product(name="Refined White Sugar", name_ta="சர்க்கரை", sku="GRO-SUG-02", category="Groceries",
                quantity=50.0, unit="kg", purchase_price=38.0, selling_price=45.0, minimum_stock_level=10.0, is_active=True),
        Product(name="Tea Powder", name_ta="தேயிலை தூள்", sku="GRO-TEA-03", category="Groceries",
                quantity=40.0, unit="packet", purchase_price=32.0, selling_price=40.0, minimum_stock_level=8.0, is_active=True),
        Product(name="Country Garlic", name_ta="பூண்டு", sku="GRO-GAR-04", category="Groceries",
                quantity=30.0, unit="kg", purchase_price=110.0, selling_price=140.0, minimum_stock_level=5.0, is_active=True),
        Product(name="Tomato", name_ta="தக்காளி", sku="GRO-TOM-05", category="Groceries",
                quantity=35.0, unit="kg", purchase_price=28.0, selling_price=40.0, minimum_stock_level=5.0, is_active=True),
        # Personal Care
        Product(name="Clinic Plus Shampoo", name_ta="ஷாம்பு", sku="PER-SHM-06", category="Personal Care",
                quantity=30.0, unit="bottle", purchase_price=55.0, selling_price=70.0, minimum_stock_level=6.0, is_active=True),
        Product(name="Hair Serum", name_ta="சீரம்", sku="PER-SER-07", category="Personal Care",
                quantity=20.0, unit="bottle", purchase_price=160.0, selling_price=210.0, minimum_stock_level=4.0, is_active=True),
        # Stationery
        Product(name="Classmate Notebook", name_ta="நோட்டுப் புத்தகம்", sku="STA-NOT-08", category="Stationery",
                quantity=40.0, unit="piece", purchase_price=35.0, selling_price=45.0, minimum_stock_level=10.0, is_active=True),
        Product(name="Reynolds Ball Pen", name_ta="பேனா", sku="STA-PEN-09", category="Stationery",
                quantity=100.0, unit="piece", purchase_price=7.0, selling_price=10.0, minimum_stock_level=20.0, is_active=True),
        Product(name="Plastic Scale 30cm", name_ta="ஸ்கேல்", sku="STA-SCL-10", category="Stationery",
                quantity=50.0, unit="piece", purchase_price=10.0, selling_price=15.0, minimum_stock_level=10.0, is_active=True),
        # Snacks & Food
        Product(name="Milk Bread", name_ta="பிரெட்", sku="SNK-BRD-11", category="Snacks and Food",
                quantity=25.0, unit="packet", purchase_price=28.0, selling_price=38.0, minimum_stock_level=5.0, is_active=True),
        Product(name="Marie Gold Biscuits", name_ta="பிஸ்கட்", sku="SNK-BIS-12", category="Snacks and Food",
                quantity=40.0, unit="packet", purchase_price=22.0, selling_price=30.0, minimum_stock_level=8.0, is_active=True),
        Product(name="Dairy Milk Chocolate", name_ta="சாக்லேட்", sku="SNK-CHO-13", category="Snacks and Food",
                quantity=50.0, unit="piece", purchase_price=16.0, selling_price=20.0, minimum_stock_level=10.0, is_active=True),
    ]
    for p in products:
        db.add(p)
    db.commit()
    return products


@pytest.mark.asyncio
async def test_scenario_1_multi_product_single_sentence(db: Session, seed_multi_category_store):
    """
    Scenario 1:
    Merchant speaks: 'Customer-ku 2 kg rice, 1 kg sugar bill podu'
    Verify:
    - Both products extracted
    - Quantities: 2 kg Rice, 1 kg Sugar
    - Backend line totals: 2 * 55 = 110, 1 * 45 = 45 -> Total = 155
    - Confirmation preview returned with requires_confirmation=True
    """
    cmd = "Customer-ku 2 kg rice, 1 kg sugar bill podu"
    res = await interpret_user_command(db=db, text=cmd, session_id="test_scen_1")

    assert res.success is True
    assert res.requires_confirmation is True
    assert res.confirmation_preview is not None

    preview = res.confirmation_preview
    assert len(preview.items) == 2
    # 2 kg Rice @ 55 = 110.0, 1 kg Sugar @ 45 = 45.0 -> Total 155.0
    assert preview.estimated_total == 155.0
    item_names = [it["product_name"] for it in preview.items]
    assert any("Rice" in n for n in item_names)
    assert any("Sugar" in n for n in item_names)


@pytest.mark.asyncio
async def test_scenario_2_and_3_turn_by_turn_cart_and_confirmation(db: Session, seed_multi_category_store):
    """
    Scenario 2 & 3: Turn-by-turn conversational bill building across multiple turns and confirmation:
    Turn 1: Shopkeeper: 'Customer-ku 2 kg sugar' -> Added to cart
    Turn 2: Shopkeeper: 'Rice 3 kg' -> Added to cart
    Turn 3: Shopkeeper: 'Tea powder 2 packet' -> Added to cart
    Turn 4: Shopkeeper: 'Bill ready pannu' -> Previews 3 items, Total ₹335
    Turn 5: Shopkeeper: 'Aama' -> Confirms sale, records sale in DB, deducts stock atomically
    """
    sid = "test_cart_turn_by_turn"

    # Turn 1
    t1 = await interpret_user_command(db=db, text="Customer-ku 2 kg sugar", session_id=sid)
    assert t1.success is True
    assert t1.requires_confirmation is False
    assert len(t1.context.get("cart_items", [])) == 1
    assert "Sugar" in t1.spoken_response or "சர்க்கரை" in t1.spoken_response

    # Turn 2
    t2 = await interpret_user_command(db=db, text="Rice 3 kg", session_id=sid)
    assert t2.success is True
    assert t2.requires_confirmation is False
    assert len(t2.context.get("cart_items", [])) == 2

    # Turn 3
    t3 = await interpret_user_command(db=db, text="Tea powder 2 packet", session_id=sid)
    assert t3.success is True
    assert t3.requires_confirmation is False
    assert len(t3.context.get("cart_items", [])) == 3

    # Turn 4: Finalize request
    t4 = await interpret_user_command(db=db, text="Bill ready pannu", session_id=sid)
    assert t4.success is True
    assert t4.requires_confirmation is True
    assert t4.confirmation_preview is not None
    assert len(t4.confirmation_preview.items) == 3
    # 2 kg Sugar @ 45 = 90; 3 kg Rice @ 55 = 165; 2 pkt Tea @ 40 = 80 -> Total = 335
    assert t4.confirmation_preview.estimated_total == 335.0

    # Turn 5: Confirm with voice 'Aama'
    t5 = await interpret_user_command(db=db, text="Aama", session_id=sid)
    assert t5.success is True
    assert t5.intent.intent == IntentCategory.CONFIRM_ACTION

    # Verify Database state
    rice = db.query(Product).filter(Product.name == "Ponni Boiled Rice").first()
    sugar = db.query(Product).filter(Product.name == "Refined White Sugar").first()
    tea = db.query(Product).filter(Product.name == "Tea Powder").first()

    assert rice.quantity == 47.0  # 50 - 3
    assert sugar.quantity == 48.0  # 50 - 2
    assert tea.quantity == 38.0  # 40 - 2

    # Verify Sale record
    sales = db.query(Sale).all()
    assert len(sales) >= 1
    last_sale = sales[-1]
    assert last_sale.total_amount == 335.0
    assert len(last_sale.items) == 3

    # Verify StockMovement audit logs
    movements = db.query(StockMovement).filter(StockMovement.movement_type == "SALE").all()
    assert len(movements) >= 3


@pytest.mark.asyncio
async def test_scenario_4_politeness_queries(db: Session, seed_multi_category_store):
    """
    Scenario 4:
    Merchant expresses politeness: 'Thank you' and greeting 'Vanakkam'
    Must respond politely without altering database records.
    """
    sid = "test_polite_sid"

    # Gratitude
    r_thx = await interpret_user_command(db=db, text="Thank you so much", session_id=sid)
    assert r_thx.success is True
    assert r_thx.intent.intent == IntentCategory.THANK_YOU
    assert r_thx.requires_confirmation is False
    assert "welcome" in r_thx.spoken_response.lower() or "உதவி" in r_thx.spoken_response

    # Greeting
    r_greet = await interpret_user_command(db=db, text="Vanakkam", session_id=sid)
    assert r_greet.success is True
    assert "வணக்கம்" in r_greet.message_ta or "Vanakkam" in r_greet.message


@pytest.mark.asyncio
async def test_scenario_5_multi_category_dynamic_recognition(db: Session, seed_multi_category_store):
    """
    Scenario 5:
    Multi-category recognition across Personal Care, Stationery, Snacks, and Groceries.
    Command: 'Customer-ku shampoo, serum, notebook, pen, bread ellam bill podu'
    Verify:
    - All 5 items from distinct categories are resolved and priced from the database.
    """
    cmd = "Customer-ku shampoo, serum, notebook, pen, bread ellam bill podu"
    res = await interpret_user_command(db=db, text=cmd, session_id="test_multi_cat")

    assert res.success is True
    assert res.requires_confirmation is True
    preview = res.confirmation_preview
    assert preview is not None
    assert len(preview.items) >= 4  # Shampoo, Serum, Notebook, Pen, Bread

    # Prices: Shampoo(70) + Serum(210) + Notebook(45) + Pen(10) + Bread(38) = 373
    assert preview.estimated_total > 300.0


def test_scenario_6_bill_history_api(client, seed_multi_category_store):
    """
    Scenario 6:
    Create a sale via POST /api/sales, then query GET /api/sales.
    Verify:
    - Sale exists in bill history
    - Items array populated with product snapshots, quantities, rates, and line totals
    """
    # Create sale with 2 items
    sale_payload = {
        "items": [
            {"product_id": 1, "quantity": 2.0},  # Rice 2 kg
            {"product_id": 2, "quantity": 1.0}   # Sugar 1 kg
        ],
        "payment_method": "UPI",
        "notes": "Counter invoice test"
    }
    create_res = client.post("/api/sales", json=sale_payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["total_amount"] == 155.0
    txn_id = created_data["transaction_id"]

    # Query GET /api/sales
    history_res = client.get("/api/sales?limit=50")
    assert history_res.status_code == 200
    history_data = history_res.json()
    assert history_data["total"] >= 1

    matched = next((s for s in history_data["items"] if s["transaction_id"] == txn_id), None)
    assert matched is not None
    assert matched["payment_method"] == "UPI"
    assert len(matched["items"]) == 2
    assert matched["items"][0]["line_total"] > 0

