# TamilVoice Kirana AI — Backend Documentation

## 1. Overview
The backend for **TamilVoice Kirana AI** is a production-grade REST API built using **FastAPI**, **SQLite**, **SQLAlchemy 2.x**, **Pydantic v2**, and **Alembic** migrations. It powers real-time inventory management, atomic retail checkout transactions, customer udhaar / credit tracking, and live business analytics for Indian Kirana shops.

---

## 2. Directory Structure

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app factory, CORS, and lifecycle seeder
│   ├── config.py                # Pydantic BaseSettings (DB URL, Timezone: Asia/Kolkata)
│   ├── database.py              # SQLite engine with foreign key PRAGMA enforcement
│   ├── database_seeder.py       # Seeds default Tamil Kirana products & opening transactions
│   │
│   ├── models/                  # SQLAlchemy 2.x Declarative Models
│   │   ├── __init__.py
│   │   ├── product.py           # Product catalog with Tamil name & stock status
│   │   ├── sale.py              # Retail sale with customer, status, payment method
│   │   ├── sale_item.py         # Line item with immutable price & name snapshot
│   │   ├── customer.py          # Customer profile & udhaar credit balance
│   │   └── stock_movement.py    # Complete inventory audit trail
│   │
│   ├── schemas/                 # Pydantic v2 Request/Response Models
│   │   ├── __init__.py
│   │   ├── product.py
│   │   ├── stock.py
│   │   ├── sale.py
│   │   ├── customer.py
│   │   ├── dashboard.py
│   │   └── reports.py
│   │
│   ├── routers/                 # Modular API Endpoints mounted at /api
│   │   ├── __init__.py
│   │   ├── health.py            # /api/health
│   │   ├── inventory.py         # /api/inventory (CRUD, filtering, search)
│   │   ├── stock.py             # /api/inventory/{id}/adjust, movements
│   │   ├── sales.py             # /api/sales (Atomic checkout, receipts)
│   │   ├── customers.py         # /api/customers
│   │   ├── dashboard.py         # /api/dashboard (Live IST KPIs)
│   │   └── reports.py           # /api/reports (Daily, products, valuation)
│   │
│   ├── services/                # Encapsulated Business Logic Layer
│   │   ├── __init__.py
│   │   ├── inventory_service.py
│   │   ├── stock_service.py
│   │   ├── sales_service.py
│   │   ├── dashboard_service.py
│   │   └── reports_service.py
│   │
│   └── utils/
│       ├── __init__.py
│       └── helpers.py           # Timezone bounds, transaction ID generator
│
├── alembic/                     # Database migrations
│   ├── versions/
│   └── env.py
├── alembic.ini
├── tests/                       # Pytest automated test suite
│   ├── conftest.py              # In-memory SQLite fixtures & TestClient
│   ├── test_health.py
│   ├── test_inventory.py
│   ├── test_stock.py
│   ├── test_sales.py            # Atomicity & price snapshot verification
│   ├── test_dashboard.py
│   └── test_reports.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## 3. Core Architectural Highlights

### A. Atomic Sales Transactions & Price Snapshots
- In retail kirana stores, product prices may fluctuate. To guarantee historical ledger integrity, `SaleItem` stores both `product_name_snapshot` and `unit_price` at the moment of checkout.
- Never trusts client-submitted totals: When `POST /api/sales` is called, prices and totals are computed exclusively server-side from active database records.
- All operations (stock deduction, sale insertion, sale items, and `StockMovement` logs) execute inside a single atomic database transaction. If any item has insufficient stock, the entire transaction rolls back cleanly.

### B. SQLite Foreign Key Enforcement
By default, SQLite does not enforce foreign keys. The connection engine in `database.py` listens for connection events and automatically executes `PRAGMA foreign_keys=ON`.

### C. IST Timezone Aggregation
Daily dashboard revenue and orders are computed using `Asia/Kolkata` day bounds (00:00:00 to 23:59:59 IST) so shopkeepers see accurate daily figures.

---

## 4. Running the Backend

### Start Server
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Run Database Migrations
```bash
python -m alembic upgrade head
```

### Run Automated Tests
```bash
python -m pytest backend/tests -v
```
