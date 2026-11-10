"""Comprehensive Kirana Catalog Seeder across 4 Categories:
1. Groceries (Rice, Sugar, Tea, Coffee, Honey, Tomato, Garlic, Masala, Oil, Flour, Salt, Bread, Biscuits)
2. Personal Care (Shampoo, Serum, Soap, Toothpaste, Hair Oil)
3. Stationery (Notebook, Pen, Scale, Pencil, Eraser, Paper)
4. Snacks & Food (Chocolates, Biscuits, Bread, Snacks)
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal
from backend.app.models.product import Product

KIRANA_CATALOG: List[Dict[str, Any]] = [
    # ---------------- Groceries ----------------
    {
        "name": "Ponni Boiled Rice",
        "name_ta": "பொன்னி புழுங்கல் அரிசி",
        "sku": "GRO-RIC-001",
        "category": "Groceries",
        "quantity": 50.0,
        "unit": "kg",
        "purchase_price": 45.0,
        "selling_price": 55.0,
        "minimum_stock_level": 10.0,
        "description": "Premium steamed Ponni boiled rice for daily meals",
        "is_active": True
    },
    {
        "name": "Refined White Sugar",
        "name_ta": "சர்க்கரை",
        "sku": "GRO-SUG-002",
        "category": "Groceries",
        "quantity": 50.0,
        "unit": "kg",
        "purchase_price": 38.0,
        "selling_price": 45.0,
        "minimum_stock_level": 10.0,
        "description": "Pure crystal white refined cane sugar",
        "is_active": True
    },
    {
        "name": "Tea Powder",
        "name_ta": "தேயிலை தூள்",
        "sku": "GRO-TEA-003",
        "category": "Groceries",
        "quantity": 40.0,
        "unit": "packet",
        "purchase_price": 32.0,
        "selling_price": 40.0,
        "minimum_stock_level": 8.0,
        "description": "Strong aromatic CTC dust tea powder",
        "is_active": True
    },
    {
        "name": "Coffee Powder",
        "name_ta": "காபி தூள்",
        "sku": "GRO-COF-004",
        "category": "Groceries",
        "quantity": 30.0,
        "unit": "packet",
        "purchase_price": 38.0,
        "selling_price": 48.0,
        "minimum_stock_level": 5.0,
        "description": "Roasted chicory blend filter coffee powder",
        "is_active": True
    },
    {
        "name": "Pure Honey",
        "name_ta": "தேன்",
        "sku": "GRO-HNY-005",
        "category": "Groceries",
        "quantity": 25.0,
        "unit": "bottle",
        "purchase_price": 140.0,
        "selling_price": 180.0,
        "minimum_stock_level": 5.0,
        "description": "Natural wild forest honey 250g glass bottle",
        "is_active": True
    },
    {
        "name": "Tomato",
        "name_ta": "தக்காளி",
        "sku": "GRO-TOM-006",
        "category": "Groceries",
        "quantity": 35.0,
        "unit": "kg",
        "purchase_price": 28.0,
        "selling_price": 40.0,
        "minimum_stock_level": 5.0,
        "description": "Fresh country red farm tomatoes",
        "is_active": True
    },
    {
        "name": "Country Garlic",
        "name_ta": "பூண்டு",
        "sku": "GRO-GAR-007",
        "category": "Groceries",
        "quantity": 25.0,
        "unit": "kg",
        "purchase_price": 110.0,
        "selling_price": 140.0,
        "minimum_stock_level": 5.0,
        "description": "Spicy mountain white garlic cloves",
        "is_active": True
    },
    {
        "name": "Onion",
        "name_ta": "வெங்காயம்",
        "sku": "GRO-ONI-008",
        "category": "Groceries",
        "quantity": 40.0,
        "unit": "kg",
        "purchase_price": 26.0,
        "selling_price": 35.0,
        "minimum_stock_level": 8.0,
        "description": "Fresh Bellary red onions",
        "is_active": True
    },
    {
        "name": "Masala Powder",
        "name_ta": "மசாலா தூள்",
        "sku": "GRO-MAS-009",
        "category": "Groceries",
        "quantity": 30.0,
        "unit": "packet",
        "purchase_price": 28.0,
        "selling_price": 35.0,
        "minimum_stock_level": 5.0,
        "description": "Aromatic curry and garam masala spice blend",
        "is_active": True
    },
    {
        "name": "Gold Winner Oil",
        "name_ta": "சூரியகாந்தி எண்ணெய்",
        "sku": "GRO-OIL-010",
        "category": "Groceries",
        "quantity": 30.0,
        "unit": "litre",
        "purchase_price": 115.0,
        "selling_price": 135.0,
        "minimum_stock_level": 6.0,
        "description": "Refined sunflower cooking oil pouch 1L",
        "is_active": True
    },
    {
        "name": "Wheat Flour",
        "name_ta": "கோதுமை மாவு",
        "sku": "GRO-WHT-011",
        "category": "Groceries",
        "quantity": 40.0,
        "unit": "kg",
        "purchase_price": 36.0,
        "selling_price": 45.0,
        "minimum_stock_level": 8.0,
        "description": "100% whole wheat stone-ground chakki atta",
        "is_active": True
    },
    {
        "name": "Tata Salt",
        "name_ta": "உப்பு",
        "sku": "GRO-SLT-012",
        "category": "Groceries",
        "quantity": 50.0,
        "unit": "packet",
        "purchase_price": 18.0,
        "selling_price": 24.0,
        "minimum_stock_level": 10.0,
        "description": "Vacuum evaporated iodized table salt 1kg",
        "is_active": True
    },

    # ---------------- Snacks & Food ----------------
    {
        "name": "Milk Bread",
        "name_ta": "பிரெட்",
        "sku": "SNK-BRD-013",
        "category": "Snacks and Food",
        "quantity": 25.0,
        "unit": "packet",
        "purchase_price": 28.0,
        "selling_price": 38.0,
        "minimum_stock_level": 5.0,
        "description": "Soft fresh daily bakery milk bread 400g",
        "is_active": True
    },
    {
        "name": "Marie Gold Biscuits",
        "name_ta": "பிஸ்கட்",
        "sku": "SNK-BIS-014",
        "category": "Snacks and Food",
        "quantity": 40.0,
        "unit": "packet",
        "purchase_price": 22.0,
        "selling_price": 30.0,
        "minimum_stock_level": 8.0,
        "description": "Crisp light tea biscuit pack",
        "is_active": True
    },
    {
        "name": "Dairy Milk Chocolate",
        "name_ta": "சாக்லேட்",
        "sku": "SNK-CHO-015",
        "category": "Snacks and Food",
        "quantity": 50.0,
        "unit": "piece",
        "purchase_price": 16.0,
        "selling_price": 20.0,
        "minimum_stock_level": 10.0,
        "description": "Cadbury milk chocolate bar",
        "is_active": True
    },
    {
        "name": "Potato Chips Snacks",
        "name_ta": "ஸ்நாக்ஸ்",
        "sku": "SNK-CHP-016",
        "category": "Snacks and Food",
        "quantity": 35.0,
        "unit": "packet",
        "purchase_price": 12.0,
        "selling_price": 15.0,
        "minimum_stock_level": 6.0,
        "description": "Crunchy salted potato wafers snack pack",
        "is_active": True
    },

    # ---------------- Personal Care ----------------
    {
        "name": "Clinic Plus Shampoo",
        "name_ta": "ஷாம்பு",
        "sku": "PER-SHM-017",
        "category": "Personal Care",
        "quantity": 30.0,
        "unit": "bottle",
        "purchase_price": 55.0,
        "selling_price": 70.0,
        "minimum_stock_level": 6.0,
        "description": "Strong and long health shampoo bottle 175ml",
        "is_active": True
    },
    {
        "name": "Hair Serum",
        "name_ta": "ஹேர் சீரம்",
        "sku": "PER-SER-018",
        "category": "Personal Care",
        "quantity": 20.0,
        "unit": "bottle",
        "purchase_price": 160.0,
        "selling_price": 210.0,
        "minimum_stock_level": 4.0,
        "description": "Smooth anti-frizz nourishing hair serum 50ml",
        "is_active": True
    },
    {
        "name": "Hamam Soap",
        "name_ta": "சோப்பு",
        "sku": "PER-SOP-019",
        "category": "Personal Care",
        "quantity": 40.0,
        "unit": "piece",
        "purchase_price": 30.0,
        "selling_price": 38.0,
        "minimum_stock_level": 8.0,
        "description": "Neem tulsi herbal bath soap bar 100g",
        "is_active": True
    },
    {
        "name": "Colgate Toothpaste",
        "name_ta": "டூத்பேஸ்ட்",
        "sku": "PER-PST-020",
        "category": "Personal Care",
        "quantity": 30.0,
        "unit": "piece",
        "purchase_price": 45.0,
        "selling_price": 58.0,
        "minimum_stock_level": 6.0,
        "description": "Strong teeth calcium dental cream 100g",
        "is_active": True
    },
    {
        "name": "Coconut Hair Oil",
        "name_ta": "தலைமுடி எண்ணெய்",
        "sku": "PER-OIL-021",
        "category": "Personal Care",
        "quantity": 25.0,
        "unit": "bottle",
        "purchase_price": 42.0,
        "selling_price": 52.0,
        "minimum_stock_level": 5.0,
        "description": "Pure filtered edible coconut hair oil bottle 100ml",
        "is_active": True
    },

    # ---------------- Stationery ----------------
    {
        "name": "Classmate Notebook",
        "name_ta": "நோட்டுப் புத்தகம்",
        "sku": "STA-NOT-022",
        "category": "Stationery",
        "quantity": 40.0,
        "unit": "piece",
        "purchase_price": 35.0,
        "selling_price": 45.0,
        "minimum_stock_level": 10.0,
        "description": "Long ruled 192 pages school exercise notebook",
        "is_active": True
    },
    {
        "name": "Reynolds Ball Pen",
        "name_ta": "பேனா",
        "sku": "STA-PEN-023",
        "category": "Stationery",
        "quantity": 60.0,
        "unit": "piece",
        "purchase_price": 7.0,
        "selling_price": 10.0,
        "minimum_stock_level": 15.0,
        "description": "Smooth blue ink fine tip writing pen",
        "is_active": True
    },
    {
        "name": "Plastic Scale 30cm",
        "name_ta": "ஸ்கேல்",
        "sku": "STA-SCL-024",
        "category": "Stationery",
        "quantity": 35.0,
        "unit": "piece",
        "purchase_price": 10.0,
        "selling_price": 15.0,
        "minimum_stock_level": 8.0,
        "description": "Transparent 30cm metric ruler with clear markings",
        "is_active": True
    },
    {
        "name": "Apsara Pencil Box",
        "name_ta": "பென்சில்",
        "sku": "STA-PNC-025",
        "category": "Stationery",
        "quantity": 25.0,
        "unit": "packet",
        "purchase_price": 42.0,
        "selling_price": 55.0,
        "minimum_stock_level": 5.0,
        "description": "Extra dark writing pencils pack of 10",
        "is_active": True
    },
    {
        "name": "Dust-Free Eraser",
        "name_ta": "அழிப்பான்",
        "sku": "STA-ERS-026",
        "category": "Stationery",
        "quantity": 50.0,
        "unit": "piece",
        "purchase_price": 3.0,
        "selling_price": 5.0,
        "minimum_stock_level": 10.0,
        "description": "Clean non-smudge soft student eraser",
        "is_active": True
    },
    {
        "name": "A4 Copier Paper",
        "name_ta": "பேப்பர்",
        "sku": "STA-PAP-027",
        "category": "Stationery",
        "quantity": 20.0,
        "unit": "packet",
        "purchase_price": 190.0,
        "selling_price": 240.0,
        "minimum_stock_level": 4.0,
        "description": "75 GSM bright white printing sheet ream 500 sheets",
        "is_active": True
    },
]


def seed_catalog(db: Session = None) -> int:
    """Seed or update all catalog products safely without resetting transaction history."""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        count = 0
        for item in KIRANA_CATALOG:
            # Check by SKU first, then by exact name
            existing = db.query(Product).filter(
                (Product.sku == item["sku"]) | (Product.name.ilike(item["name"]))
            ).first()

            if existing:
                # Update metadata while preserving merchant's current stock if positive
                existing.name_ta = item["name_ta"]
                existing.category = item["category"]
                existing.selling_price = item["selling_price"]
                existing.purchase_price = item["purchase_price"]
                existing.unit = item["unit"]
                existing.minimum_stock_level = item["minimum_stock_level"]
                existing.is_active = True
                if existing.quantity <= 0:
                    existing.quantity = item["quantity"]
            else:
                new_prod = Product(**item)
                db.add(new_prod)
                count += 1

        db.commit()
        return count
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    added = seed_catalog()
    print(f"Catalog updated. {added} new products added.")

