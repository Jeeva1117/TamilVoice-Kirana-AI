"""Comprehensive Verification of Real Conversational Shopkeeper Workflow."""
import asyncio
import sys
import os

sys.path.insert(0, r"c:\Users\acer\Desktop\TamilVoice Kirana AI")

from backend.app.database import SessionLocal
from backend.app.models.product import Product
from backend.app.services.ai_service import interpret_user_command, confirm_pending_action


async def run_tests():
    # Reset baseline test store quantities
    import sqlite3
    conn = sqlite3.connect('kirana_ai.db')
    c = conn.cursor()
    c.execute("UPDATE products SET quantity = 15.0, selling_price = 45.0, is_active = 1 WHERE name = 'Wheat Flour'")
    c.execute("UPDATE products SET quantity = 20.0, selling_price = 135.0, is_active = 1 WHERE name = 'Gold Winner Oil'")
    c.execute("UPDATE products SET quantity = 30.0, selling_price = 55.0, is_active = 1 WHERE name LIKE '%rice%'")
    c.execute("UPDATE products SET quantity = 25.0, selling_price = 40.0, is_active = 1 WHERE name = 'Tomato'")
    c.execute("UPDATE products SET quantity = 30.0, selling_price = 35.0, is_active = 1 WHERE name = 'Onion'")
    c.execute("UPDATE products SET quantity = 20.0, selling_price = 28.0, is_active = 1 WHERE name = 'Milk'")
    c.execute("UPDATE products SET quantity = 25.0, selling_price = 45.0, is_active = 1 WHERE name = 'Sugar'")
    c.execute("UPDATE products SET quantity = 20.0, selling_price = 40.0, is_active = 1 WHERE name = 'Tea Powder'")
    conn.commit()
    conn.close()

    db = SessionLocal()
    print("=" * 60)
    print("STARTING REAL CONVERSATIONAL SHOPKEEPER WORKFLOW VERIFICATION")
    print("=" * 60)

    # -------------------------------------------------------------
    # Test 1: Scenario 1 - Conversational Stock Addition
    # "10 kilo godhumai maavu stock add pannunga"
    # -------------------------------------------------------------
    print("\n--- Test 1: '10 kilo godhumai maavu stock add pannunga' ---")
    res1 = await interpret_user_command(db, "10 kilo godhumai maavu stock add pannunga", allow_mock=True)
    print("Success:", res1.success)
    print("Message (Ta):", res1.message_ta)
    print("Requires Confirmation:", res1.requires_confirmation)
    assert res1.requires_confirmation is True
    assert "Wheat Flour 10 kg stock add pannalama?" in res1.message_ta
    action_id_1 = res1.confirmation_preview.action_id

    # Confirm action
    confirm_res1 = confirm_pending_action(db, action_id_1)
    print("Confirm Msg:", confirm_res1.message_ta)
    print("New Stock:", confirm_res1.new_stock)
    assert "Wheat Flour 10 kg stock add panniyachu. Ippo total stock 25 kg irukku." in confirm_res1.message_ta
    assert confirm_res1.new_stock == 25.0

    # Verify DB
    p_wheat = db.query(Product).filter(Product.name == "Wheat Flour").first()
    assert p_wheat.quantity == 25.0
    print("Verified DB Stock for Wheat Flour:", p_wheat.quantity)

    # -------------------------------------------------------------
    # Test 2: Scenario 2 - Conversational Stock Addition
    # "15 litres Gold Winner oil add pannunga"
    # -------------------------------------------------------------
    print("\n--- Test 2: '15 litres Gold Winner oil add pannunga' ---")
    res2 = await interpret_user_command(db, "15 litres Gold Winner oil add pannunga", allow_mock=True)
    print("Message (Ta):", res2.message_ta)
    assert res2.requires_confirmation is True
    assert "Gold Winner Oil 15 litre stock add pannalama?" in res2.message_ta
    action_id_2 = res2.confirmation_preview.action_id

    confirm_res2 = confirm_pending_action(db, action_id_2)
    print("Confirm Msg:", confirm_res2.message_ta)
    assert "Gold Winner Oil 15 litre stock add panniyachu. Ippo total stock 35 litre irukku." in confirm_res2.message_ta
    assert confirm_res2.new_stock == 35.0

    p_oil = db.query(Product).filter(Product.name == "Gold Winner Oil").first()
    assert p_oil.quantity == 35.0
    print("Verified DB Stock for Gold Winner Oil:", p_oil.quantity)

    # -------------------------------------------------------------
    # Test 3: Scenario 3 - Clarification Follow-up
    # "Gold Winner oil add pannunga" (no quantity provided)
    # -------------------------------------------------------------
    print("\n--- Test 3: 'Gold Winner oil add pannunga' (missing quantity) ---")
    res3 = await interpret_user_command(db, "Gold Winner oil add pannunga", allow_mock=True)
    print("Clarification Question:", res3.message_ta)
    assert res3.requires_confirmation is False
    assert res3.intent.requires_clarification is True
    assert "Evlo litre Gold Winner Oil add pannanum?" in res3.message_ta

    # -------------------------------------------------------------
    # Test 4: Scenario 4 - Stock Query
    # "Rice stock evlo irukku?"
    # -------------------------------------------------------------
    print("\n--- Test 4: 'Rice stock evlo irukku?' ---")
    res4 = await interpret_user_command(db, "Rice stock evlo irukku?", allow_mock=True)
    print("Query Response:", res4.message_ta)
    assert "Ponni Boiled Rice stock 30 kg irukku." in res4.message_ta

    # -------------------------------------------------------------
    # Test 5: Scenario 5 - Multi-Item Customer Sale
    # "Customer-ku one kilo tomato, two kilo onion, three kilo rice, two litre milk, two packet sugar, two packet tea powder sale pannunga"
    # -------------------------------------------------------------
    print("\n--- Test 5: Multi-Item Customer Sale ---")
    cmd_sale = "Customer-ku one kilo tomato, two kilo onion, three kilo rice, two litre milk, two packet sugar, two packet tea powder sale pannunga"
    res5 = await interpret_user_command(db, cmd_sale, allow_mock=True)
    print("Sale Order Message:", res5.message_ta)
    assert res5.requires_confirmation is True
    assert "Customer order ready. Bill total ₹501. Sale confirm pannalama?" in res5.message_ta
    
    # Check item preview
    items = res5.confirmation_preview.items
    print(f"Items count: {len(items)}")
    for it in items:
        print(f"  - {it['product_name']}: {it['quantity']} {it['unit']} @ ₹{it['unit_price']} = ₹{it['line_total']}")
    assert len(items) == 6
    assert res5.confirmation_preview.estimated_total == 501.0

    action_id_5 = res5.confirmation_preview.action_id
    confirm_res5 = confirm_pending_action(db, action_id_5)
    print("Confirm Spoken Bill:", confirm_res5.message_ta)
    assert "Bill successfully create panniyachu." in confirm_res5.message_ta
    assert "Total bill 501 rupees. Customer-kitta collect pannunga." in confirm_res5.message_ta

    # Verify atomic DB stock deductions
    p_tomato = db.query(Product).filter(Product.name == "Tomato").first()
    p_onion = db.query(Product).filter(Product.name == "Onion").first()
    p_rice = db.query(Product).filter(Product.name == "Ponni Boiled Rice").first()
    p_milk = db.query(Product).filter(Product.name == "Milk").first()
    p_sugar = db.query(Product).filter(Product.name == "Sugar").first()
    p_tea = db.query(Product).filter(Product.name == "Tea Powder").first()

    assert p_tomato.quantity == 24.0  # was 25 - 1
    assert p_onion.quantity == 28.0   # was 30 - 2
    assert p_rice.quantity == 27.0    # was 30 - 3
    assert p_milk.quantity == 18.0    # was 20 - 2
    assert p_sugar.quantity == 23.0   # was 25 - 2
    assert p_tea.quantity == 18.0     # was 20 - 2
    print("All 6 product stocks atomically deducted in SQLite kirana_ai.db!")

    # -------------------------------------------------------------
    # Test 6: Scenario 6 - Daily Reports & Queries
    # -------------------------------------------------------------
    print("\n--- Test 6: Daily Reports & Queries ---")
    res_sales = await interpret_user_command(db, "Innaiku sales evlo?", allow_mock=True)
    print("Sales:", res_sales.message_ta)
    assert "Innaiku total sales" in res_sales.message_ta and "rupees." in res_sales.message_ta

    res_bills = await interpret_user_command(db, "Innaiku ethana bill potten?", allow_mock=True)
    print("Bills:", res_bills.message_ta)
    assert "Total" in res_bills.message_ta and "bills create pannirukkinga." in res_bills.message_ta

    res_best = await interpret_user_command(db, "Innaiku best selling product enna?", allow_mock=True)
    print("Best Selling:", res_best.message_ta)
    assert "Innaiku best selling product" in res_best.message_ta

    res_low = await interpret_user_command(db, "Low stock products sollu", allow_mock=True)
    print("Low Stock:", res_low.message_ta)
    assert "Ellam products-um nalla stock irukku. No low stock alerts." in res_low.message_ta

    # -------------------------------------------------------------
    # Test 7: Non-existent product query
    # "5 kilo Dragon Fruit add pannunga"
    # -------------------------------------------------------------
    print("\n--- Test 7: Non-existent product ---")
    res7 = await interpret_user_command(db, "5 kilo Dragon Fruit add pannunga", allow_mock=True)
    print("Non-existent:", res7.message_ta)
    assert "Dragon Fruit product list-la illa. First product add pannalama?" in res7.message_ta

    print("\n" + "=" * 60)
    print("ALL CONVERSATIONAL WORKFLOW UNIT TESTS PASSED PERFECTLY!")
    print("=" * 60)
    db.close()

if __name__ == "__main__":
    asyncio.run(run_tests())
