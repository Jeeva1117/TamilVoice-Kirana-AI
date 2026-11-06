"""Database Seeder: Populates initial realistic Kirana products, customers, and test sales."""
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from backend.app.models.product import Product
from backend.app.models.customer import Customer
from backend.app.models.sale import Sale
from backend.app.models.sale_item import SaleItem
from backend.app.models.stock_movement import StockMovement
from backend.app.utils.helpers import generate_transaction_id


SEED_PRODUCTS = [
    {
        "name": "Ponni Boiled Rice",
        "name_ta": "பொன்னி புழுங்கல் அரிசி",
        "sku": "RIC-PON-001",
        "category": "Rice & Grains",
        "quantity": 50.0,
        "unit": "kg",
        "purchase_price": 52.0,
        "selling_price": 60.0,
        "minimum_stock_level": 10.0,
        "description": "High quality steamed Ponni rice for daily meals",
    },
    {
        "name": "Toor Dal First Quality",
        "name_ta": "துவரம் பருப்பு",
        "sku": "DAL-TOO-002",
        "category": "Dal & Pulses",
        "quantity": 35.0,
        "unit": "kg",
        "purchase_price": 140.0,
        "selling_price": 165.0,
        "minimum_stock_level": 8.0,
        "description": "Unpolished aromatic toor dal for sambar",
    },
    {
        "name": "Gold Winner Sunflower Oil 1L",
        "name_ta": "சூரியகாந்தி எண்ணெய்",
        "sku": "OIL-SUN-003",
        "category": "Oils & Ghee",
        "quantity": 24.0,
        "unit": "litre",
        "purchase_price": 125.0,
        "selling_price": 145.0,
        "minimum_stock_level": 6.0,
        "description": "Refined sunflower cooking oil with vitamins A & D",
    },
    {
        "name": "Aashirvaad Sharbati Atta 5kg",
        "name_ta": "கோதுமை மாவு",
        "sku": "FLR-ATT-004",
        "category": "Flours",
        "quantity": 15.0,
        "unit": "packet",
        "purchase_price": 230.0,
        "selling_price": 265.0,
        "minimum_stock_level": 5.0,
        "description": "100% whole wheat flour for soft rotis",
    },
    {
        "name": "Tata Salt Vacuum Evaporated",
        "name_ta": "உப்பு",
        "sku": "SPC-SLT-005",
        "category": "Spices & Seasoning",
        "quantity": 40.0,
        "unit": "packet",
        "purchase_price": 22.0,
        "selling_price": 28.0,
        "minimum_stock_level": 10.0,
        "description": "Desh Ka Namak iodized salt 1kg pack",
    },
    {
        "name": "Refined White Sugar",
        "name_ta": "சர்க்கரை",
        "sku": "ESS-SUG-006",
        "category": "Essentials",
        "quantity": 60.0,
        "unit": "kg",
        "purchase_price": 40.0,
        "selling_price": 46.0,
        "minimum_stock_level": 15.0,
        "description": "Sulphur-free clean white crystal sugar",
    },
    {
        "name": "Aavin Toned Fresh Milk 500ml",
        "name_ta": "ஆவின் பால்",
        "sku": "DAR-MLK-007",
        "category": "Dairy",
        "quantity": 30.0,
        "unit": "packet",
        "purchase_price": 22.0,
        "selling_price": 25.0,
        "minimum_stock_level": 10.0,
        "description": "Pasteurized fresh toned milk in blue sachet",
    },
    {
        "name": "Guntur Red Chili Stemless",
        "name_ta": "மிளகாய் வற்றல்",
        "sku": "SPC-CHI-008",
        "category": "Spices & Seasoning",
        "quantity": 6.0,
        "unit": "kg",
        "purchase_price": 210.0,
        "selling_price": 260.0,
        "minimum_stock_level": 10.0,
        "description": "Spicy hot sun-dried red chilies (low stock)",
    },
    {
        "name": "Mysore Sandal Premium Soap",
        "name_ta": "மைசூர் சந்தன சோப்பு",
        "sku": "PRC-SAN-009",
        "category": "Personal Care",
        "quantity": 0.0,
        "unit": "pcs",
        "purchase_price": 48.0,
        "selling_price": 60.0,
        "minimum_stock_level": 10.0,
        "description": "Pure sandalwood oil herbal bath soap (out of stock)",
    },
    {
        "name": "Bru Instant Coffee 50g",
        "name_ta": "ப்ரூ காபி தூள்",
        "sku": "BEV-BRU-010",
        "category": "Beverages",
        "quantity": 25.0,
        "unit": "packet",
        "purchase_price": 78.0,
        "selling_price": 92.0,
        "minimum_stock_level": 5.0,
        "description": "Roasted chicory & coffee blend",
    },
    {
        "name": "Farm Fresh Country Eggs",
        "name_ta": "நாட்டுக்கோழி முட்டை",
        "sku": "EGG-CNT-011",
        "category": "Dairy & Eggs",
        "quantity": 72.0,
        "unit": "pcs",
        "purchase_price": 8.0,
        "selling_price": 11.0,
        "minimum_stock_level": 20.0,
        "description": "Natural protein-rich free-range eggs",
    },
    {
        "name": "Urad Dal White Whole",
        "name_ta": "உளுத்தம் பருப்பு",
        "sku": "DAL-URD-012",
        "category": "Dal & Pulses",
        "quantity": 22.0,
        "unit": "kg",
        "purchase_price": 130.0,
        "selling_price": 155.0,
        "minimum_stock_level": 5.0,
        "description": "Cleaned white urad dal for soft idlis and crispy dosas",
    },
]

SEED_CUSTOMERS = [
    {"name": "Murugan K.", "phone": "9876543210", "address": "14 Sannadhi Street, Madurai", "credit_balance": 450.0},
    {"name": "Selvi Raman", "phone": "9443322110", "address": "8 Market Road, Madurai", "credit_balance": 0.0},
    {"name": "Ramesh Kumar", "phone": "9123456780", "address": "22 North Car Street, Madurai", "credit_balance": 180.0},
    {"name": "Priya Sundar", "phone": "9840123456", "address": "5 West Street, Madurai", "credit_balance": 0.0},
]


def seed_database(db: Session):
    """Seed default catalog and test data if database is empty."""
    product_count = db.query(Product).count()
    if product_count > 0:
        return  # Database already seeded

    # 1. Seed Products
    created_products = []
    for item in SEED_PRODUCTS:
        prod = Product(**item, is_active=True)
        db.add(prod)
        db.flush()
        created_products.append(prod)

        # Initial stock movement
        if prod.quantity > 0:
            mv = StockMovement(
                product_id=prod.id,
                movement_type="PURCHASE",
                quantity=prod.quantity,
                previous_quantity=0.0,
                new_quantity=prod.quantity,
                reason="Initial inventory opening stock",
                reference_id=f"INIT-{prod.sku}"
            )
            db.add(mv)

    # 2. Seed Customers
    created_customers = []
    for c_data in SEED_CUSTOMERS:
        cust = Customer(**c_data)
        db.add(cust)
        db.flush()
        created_customers.append(cust)

    # 3. Seed Sample Completed Sales (for rich initial dashboard stats)
    now = datetime.now(timezone.utc)
    # Today sale 1
    p1 = created_products[0]  # Ponni rice
    p2 = created_products[2]  # Oil
    qty1, qty2 = 5.0, 2.0
    line1 = round(qty1 * p1.selling_price, 2)
    line2 = round(qty2 * p2.selling_price, 2)
    tot1 = line1 + line2

    txn1 = generate_transaction_id()
    sale1 = Sale(
        transaction_id=txn1,
        customer_id=created_customers[0].id,
        total_amount=tot1,
        payment_method="CASH",
        status="COMPLETED",
        notes="Opening demo transaction",
        created_at=now - timedelta(hours=2)
    )
    db.add(sale1)
    db.flush()

    item1 = SaleItem(
        sale_id=sale1.id,
        product_id=p1.id,
        product_name_snapshot=p1.name,
        quantity=qty1,
        unit=p1.unit,
        unit_price=p1.selling_price,
        line_total=line1
    )
    item2 = SaleItem(
        sale_id=sale1.id,
        product_id=p2.id,
        product_name_snapshot=p2.name,
        quantity=qty2,
        unit=p2.unit,
        unit_price=p2.selling_price,
        line_total=line2
    )
    db.add_all([item1, item2])

    # Today sale 2 (UPI)
    p3 = created_products[1]  # Toor dal
    qty3 = 2.0
    line3 = round(qty3 * p3.selling_price, 2)
    txn2 = generate_transaction_id()
    sale2 = Sale(
        transaction_id=txn2,
        customer_id=created_customers[1].id,
        total_amount=line3,
        payment_method="UPI",
        status="COMPLETED",
        notes="GPay payment",
        created_at=now - timedelta(hours=1)
    )
    db.add(sale2)
    db.flush()
    item3 = SaleItem(
        sale_id=sale2.id,
        product_id=p3.id,
        product_name_snapshot=p3.name,
        quantity=qty3,
        unit=p3.unit,
        unit_price=p3.selling_price,
        line_total=line3
    )
    db.add(item3)

    db.commit()
