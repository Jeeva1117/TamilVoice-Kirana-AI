"""Seed Clean Demonstration Inventory for TamilVoice Kirana AI.
Uses SQLAlchemy session and Product model to ensure schema integrity.
"""
from datetime import datetime, timezone
from backend.app.database import SessionLocal
from backend.app.models.product import Product

CLEAN_PRODUCTS = [
    {
        "name": "Ponni Boiled Rice",
        "name_ta": "பொன்னி புழுங்கல் அரிசி",
        "sku": "RIC-PON-001",
        "category": "Grains & Flours",
        "quantity": 25.0,
        "unit": "kg",
        "purchase_price": 45.0,
        "selling_price": 55.0,
        "minimum_stock_level": 10.0,
        "description": "Premium Ponni steamed boiled rice",
        "is_active": True
    },
    {
        "name": "Sugar",
        "name_ta": "சர்க்கரை",
        "sku": "SUG-WHT-001",
        "category": "Groceries",
        "quantity": 25.0,
        "unit": "kg",
        "purchase_price": 38.0,
        "selling_price": 45.0,
        "minimum_stock_level": 5.0,
        "description": "Refined pure white cane sugar",
        "is_active": True
    },
    {
        "name": "Tea Powder",
        "name_ta": "தேயிலை தூள்",
        "sku": "TEA-DST-001",
        "category": "Beverages",
        "quantity": 20.0,
        "unit": "packet",
        "purchase_price": 32.0,
        "selling_price": 40.0,
        "minimum_stock_level": 5.0,
        "description": "Strong aromatic CTC dust tea powder",
        "is_active": True
    },
    {
        "name": "Tomato",
        "name_ta": "தக்காளி",
        "sku": "VEG-TOM-001",
        "category": "Vegetables",
        "quantity": 20.0,
        "unit": "kg",
        "purchase_price": 28.0,
        "selling_price": 40.0,
        "minimum_stock_level": 5.0,
        "description": "Fresh country red tomatoes",
        "is_active": True
    },
    {
        "name": "Pure Honey",
        "name_ta": "தேன்",
        "sku": "HNY-NAT-001",
        "category": "Groceries",
        "quantity": 15.0,
        "unit": "bottle",
        "purchase_price": 140.0,
        "selling_price": 180.0,
        "minimum_stock_level": 3.0,
        "description": "100% natural pure wild honey (500g glass bottle)",
        "is_active": True
    },
    {
        "name": "Onion",
        "name_ta": "வெங்காயம்",
        "sku": "VEG-ONI-001",
        "category": "Vegetables",
        "quantity": 25.0,
        "unit": "kg",
        "purchase_price": 26.0,
        "selling_price": 35.0,
        "minimum_stock_level": 5.0,
        "description": "Fresh Bellary onions",
        "is_active": True
    },
    {
        "name": "Milk",
        "name_ta": "பால்",
        "sku": "DRY-MLK-001",
        "category": "Dairy",
        "quantity": 20.0,
        "unit": "litre",
        "purchase_price": 24.0,
        "selling_price": 28.0,
        "minimum_stock_level": 5.0,
        "description": "Fresh pasteurized standardized milk",
        "is_active": True
    },
    {
        "name": "Wheat Flour",
        "name_ta": "கோதுமை மாவு",
        "sku": "FLR-WHT-001",
        "category": "Grains & Flours",
        "quantity": 20.0,
        "unit": "kg",
        "purchase_price": 36.0,
        "selling_price": 45.0,
        "minimum_stock_level": 5.0,
        "description": "Whole wheat flour for chapatis",
        "is_active": True
    },
    {
        "name": "Gold Winner Oil",
        "name_ta": "சூரியகாந்தி எண்ணெய்",
        "sku": "OIL-SUN-001",
        "category": "Oils & Ghee",
        "quantity": 20.0,
        "unit": "litre",
        "purchase_price": 115.0,
        "selling_price": 135.0,
        "minimum_stock_level": 5.0,
        "description": "Refined sunflower cooking oil",
        "is_active": True
    },
    {
        "name": "Masala Powder",
        "name_ta": "மசாலா தூள்",
        "sku": "SPC-MAS-001",
        "category": "Spices",
        "quantity": 15.0,
        "unit": "packet",
        "purchase_price": 25.0,
        "selling_price": 35.0,
        "minimum_stock_level": 5.0,
        "description": "Traditional aromatic sambar & curry masala powder",
        "is_active": True
    }
]


def seed_clean_inventory():
    db = SessionLocal()
    try:
        # 1. Clean up temporary test/audit items safely
        audit_items = db.query(Product).filter(
            (Product.name.like("Audit%")) | (Product.name.like("Test%"))
        ).all()
        for it in audit_items:
            db.delete(it)
        db.commit()

        # 2. Upsert each clean product
        for p_data in CLEAN_PRODUCTS:
            prod = db.query(Product).filter(
                (Product.name == p_data["name"]) | (Product.name_ta == p_data["name_ta"]) | (Product.sku == p_data["sku"])
            ).first()

            if prod:
                prod.name = p_data["name"]
                prod.name_ta = p_data["name_ta"]
                prod.sku = p_data["sku"]
                prod.category = p_data["category"]
                prod.quantity = p_data["quantity"]
                prod.unit = p_data["unit"]
                prod.purchase_price = p_data["purchase_price"]
                prod.selling_price = p_data["selling_price"]
                prod.minimum_stock_level = p_data["minimum_stock_level"]
                prod.description = p_data["description"]
                prod.is_active = True
                prod.updated_at = datetime.now(timezone.utc)
            else:
                new_prod = Product(**p_data)
                db.add(new_prod)

        db.commit()

        # Verify
        active_prods = db.query(Product).filter(Product.is_active == True).all()
        print(f"Clean inventory initialized with {len(active_prods)} active products:")
        for r in active_prods:
            print(f"  [{r.id}] {r.name} ({r.name_ta}) - {r.quantity} {r.unit} @ Rs {r.selling_price}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_clean_inventory()
