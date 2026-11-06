"""
TamilVoice Kirana AI - FastAPI Application Server
Main entry point for REST API, voice processing pipeline, and database initialization.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base, SessionLocal
from backend.models import Product, Sale
from backend.routers import dashboard, inventory, sales, voice, reports


def seed_initial_data():
    """Populate initial realistic Kirana products and transactions if database is empty."""
    db = SessionLocal()
    try:
        if db.query(Product).count() == 0:
            sample_products = [
                Product(
                    sku="SKU-RIC-001",
                    name_en="Ponni Boiled Rice 25kg",
                    name_ta="பொன்னி புழுங்கல் அரிசி 25kg",
                    category="Rice",
                    stock=2.0,
                    min_stock=8.0,
                    unit="bags",
                    purchase_price=1250.0,
                    selling_price=1450.0
                ),
                Product(
                    sku="SKU-OIL-002",
                    name_en="Gold Winner Sunflower Oil 1L",
                    name_ta="கோல்ட் வின்னர் எண்ணெய் 1L",
                    category="Oil",
                    stock=4.0,
                    min_stock=15.0,
                    unit="packets",
                    purchase_price=120.0,
                    selling_price=140.0
                ),
                Product(
                    sku="SKU-SPI-003",
                    name_en="Aachi Chilli Powder 100g",
                    name_ta="ஆச்சி மிளகாய் தூள் 100g",
                    category="Spices",
                    stock=6.0,
                    min_stock=20.0,
                    unit="packets",
                    purchase_price=38.0,
                    selling_price=48.0
                ),
                Product(
                    sku="SKU-GRO-004",
                    name_en="Tata Iodized Salt 1kg",
                    name_ta="டாடா அயோடின் உப்பு 1kg",
                    category="Grocery",
                    stock=3.0,
                    min_stock=12.0,
                    unit="packets",
                    purchase_price=20.0,
                    selling_price=26.0
                ),
                Product(
                    sku="SKU-DHA-005",
                    name_en="Premium Toor Dhal",
                    name_ta="முதல் தர துவரம் பருப்பு",
                    category="Dhal",
                    stock=5.0,
                    min_stock=18.0,
                    unit="kg",
                    purchase_price=130.0,
                    selling_price=155.0
                ),
                Product(
                    sku="SKU-FLO-006",
                    name_en="Aashirvaad Whole Wheat Atta 5kg",
                    name_ta="ஆசீர்வாத் கோதுமை மாவு 5kg",
                    category="Flour",
                    stock=14.0,
                    min_stock=10.0,
                    unit="packets",
                    purchase_price=250.0,
                    selling_price=295.0
                ),
                Product(
                    sku="SKU-SUG-007",
                    name_en="Refined White Sugar",
                    name_ta="சுத்திகரிக்கப்பட்ட சீனி",
                    category="Sugar",
                    stock=45.0,
                    min_stock=20.0,
                    unit="kg",
                    purchase_price=40.0,
                    selling_price=48.0
                ),
                Product(
                    sku="SKU-TEA-008",
                    name_en="3 Roses Tea Dust 500g",
                    name_ta="3 ரோஸஸ் டீ தூள் 500g",
                    category="Grocery",
                    stock=18.0,
                    min_stock=10.0,
                    unit="packets",
                    purchase_price=280.0,
                    selling_price=330.0
                )
            ]
            db.add_all(sample_products)
            db.commit()
            print("[FastAPI] Seeded 8 initial Kirana inventory items.")

        if db.query(Sale).count() == 0:
            sample_sales = [
                Sale(
                    invoice_number="KB-1089",
                    items_summary_en="Ponni Rice 25kg (1 bag)",
                    items_summary_ta="பொன்னி அரிசி 25kg (1 மூட்டை)",
                    total_amount=1450.0,
                    payment_method="UPI",
                    status="completed"
                ),
                Sale(
                    invoice_number="KB-1088",
                    items_summary_en="Sunflower Oil 2L + Tata Salt 1kg",
                    items_summary_ta="சூரியகாந்தி எண்ணெய் 2L + உப்பு 1kg",
                    total_amount=320.0,
                    payment_method="Cash",
                    status="completed"
                ),
                Sale(
                    invoice_number="KB-1087",
                    items_summary_en="Aachi Chilli & Coriander Powder",
                    items_summary_ta="ஆச்சி மிளகாய் & மல்லி தூள்",
                    total_amount=95.0,
                    payment_method="Cash",
                    status="completed"
                ),
                Sale(
                    invoice_number="KB-1086",
                    items_summary_en="White Sugar 5kg + Toor Dhal 2kg",
                    items_summary_ta="சீனி 5kg + துவரம் பருப்பு 2kg",
                    total_amount=460.0,
                    payment_method="UPI",
                    status="completed"
                ),
                Sale(
                    invoice_number="KB-1085",
                    items_summary_en="Aashirvaad Whole Wheat Atta 5kg",
                    items_summary_ta="ஆசீர்வாத் கோதுமை மாவு 5kg",
                    total_amount=295.0,
                    payment_method="Cash",
                    status="completed"
                )
            ]
            db.add_all(sample_sales)
            db.commit()
            print("[FastAPI] Seeded initial billing history.")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables and seed data
    Base.metadata.create_all(bind=engine)
    seed_initial_data()
    yield
    # Shutdown logic if any


app = FastAPI(
    title="TamilVoice Kirana AI API",
    description="High-performance backend API for voice-first Indian Kirana store management.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware Configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers under /api
app.include_router(dashboard.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(sales.router, prefix="/api")
app.include_router(voice.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


@app.get("/")
def root():
    return {
        "app": "TamilVoice Kirana AI",
        "status": "online",
        "docs_url": "/docs",
        "api_prefix": "/api"
    }


@app.get("/api/health")
def healthcheck():
    return {
        "status": "healthy",
        "database": "connected",
        "service": "FastAPI TamilVoice Backend"
    }
