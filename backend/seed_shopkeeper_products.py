"""Seed real shopkeeper test products into SQLite database kirana_ai.db."""
import sqlite3
import datetime

conn = sqlite3.connect('kirana_ai.db')
c = conn.cursor()

products = [
    ('Wheat Flour', 'கோதுமை மாவு', 'SKU-WHEAT-001', 'Flour', 15.0, 'kg', 35.0, 45.0, 5.0, 'Quality Chakki Fresh Wheat Flour', 1),
    ('Gold Winner Oil', 'சூரியகாந்தி எண்ணெய்', 'SKU-OIL-001', 'Oil', 20.0, 'litre', 115.0, 135.0, 5.0, 'Refined Sunflower Oil 1L pouch', 1),
    ('Tomato', 'தக்காளி', 'SKU-TOMATO-001', 'Vegetables', 25.0, 'kg', 28.0, 40.0, 5.0, 'Fresh Country Tomatoes', 1),
    ('Onion', 'வெங்காயம்', 'SKU-ONION-001', 'Vegetables', 30.0, 'kg', 24.0, 35.0, 5.0, 'Fresh Bellary Onion', 1),
    ('Milk', 'பால்', 'SKU-MILK-001', 'Dairy', 20.0, 'litre', 22.0, 28.0, 5.0, 'Standardized Pasteurized Milk 500ml', 1),
    ('Sugar', 'சர்க்கரை', 'SKU-SUGAR-001', 'Grocery', 25.0, 'packet', 36.0, 45.0, 5.0, 'Refined White Sugar 1kg pkt', 1),
    ('Tea Powder', 'டீ தூள்', 'SKU-TEA-001', 'Beverages', 20.0, 'packet', 30.0, 40.0, 5.0, 'Premium Dust Tea 250g', 1)
]

now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
for p in products:
    c.execute('SELECT id FROM products WHERE name = ?', (p[0],))
    existing = c.fetchone()
    if existing:
        c.execute('UPDATE products SET quantity = ?, selling_price = ? WHERE id = ?', (p[4], p[7], existing[0]))
    else:
        c.execute('''
            INSERT INTO products 
            (name, name_ta, sku, category, quantity, unit, purchase_price, selling_price, minimum_stock_level, description, is_active, created_at, updated_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (*p, now_str, now_str))

# Also ensure Ponni Boiled Rice is active and 30.0 kg
c.execute("UPDATE products SET quantity = 30.0, selling_price = 55.0, is_active = 1 WHERE name LIKE '%rice%'")

conn.commit()

c.execute('SELECT id, name, name_ta, quantity, unit, selling_price FROM products')
rows = c.fetchall()
print(f"TOTAL PRODUCTS IN DB: {len(rows)}")
for r in rows:
    print(r)

conn.close()
