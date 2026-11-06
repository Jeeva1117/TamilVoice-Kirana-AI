# TamilVoice Kirana AI — Backend Documentation

## 1. Overview
The backend for **TamilVoice Kirana AI** is a production-grade REST API built using **FastAPI**, **SQLite**, **SQLAlchemy 2.x**, **Pydantic v2**, **Alembic**, and the **Google Gemini GenAI SDK**. It powers real-time inventory management, atomic retail checkout transactions, customer udhaar / credit tracking, live business analytics, and a Tamil/Tanglish Natural Language Voice Intelligence Engine for Indian Kirana shops.

---

## 2. Directory Structure

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app factory, CORS, and lifespan seeder
│   ├── config.py                # Pydantic BaseSettings (DB URL, Gemini config, Timezone: Asia/Kolkata)
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
│   │   ├── product.py           # Product schemas
│   │   ├── stock.py             # Stock adjustment schemas
│   │   ├── sale.py              # Sales & checkout schemas
│   │   ├── customer.py          # Customer profile schemas
│   │   ├── dashboard.py         # Real-time dashboard KPIs
│   │   ├── reports.py           # Daily & product analytics
│   │   ├── ai.py                # Intent categories, entities, confirmation previews
│   │   └── voice.py             # Voice simulation schemas
│   │
│   ├── routers/                 # Modular API Endpoints mounted at /api
│   │   ├── __init__.py
│   │   ├── health.py            # /api/health
│   │   ├── inventory.py         # /api/inventory (CRUD, filtering, search)
│   │   ├── stock.py             # /api/inventory/{id}/adjust, movements
│   │   ├── sales.py             # /api/sales (Atomic checkout, receipts)
│   │   ├── customers.py         # /api/customers
│   │   ├── dashboard.py         # /api/dashboard (Live IST KPIs)
│   │   ├── reports.py           # /api/reports (Daily, products, valuation)
│   │   ├── ai.py                # /api/ai/interpret, confirm, cancel, status
│   │   └── voice.py             # /api/voice/process
│   │
│   ├── services/                # Encapsulated Business Logic Layer
│   │   ├── __init__.py
│   │   ├── inventory_service.py # Catalog querying, multi-field search, SKU deduplication
│   │   ├── stock_service.py     # Atomic stock adjustments with validation & audit logs
│   │   ├── sales_service.py     # Atomic checkout transactions, stock deduction & snapshots
│   │   ├── dashboard_service.py # IST date aggregation, top products, recent activity
│   │   ├── reports_service.py   # Daily sales summaries and inventory valuation
│   │   ├── product_resolver.py  # Bilingual Tamil/Tanglish/English catalog matching
│   │   ├── gemini_client.py     # Official Google GenAI SDK intent extraction
│   │   └── ai_service.py        # AI orchestration, safe confirmation preview, TTL store
│   │
│   └── utils/
│       ├── __init__.py
│       └── helpers.py           # Timezone bounds, transaction ID generator
│
├── alembic/                     # Database migrations
│   ├── versions/
│   └── env.py
├── alembic.ini
├── tests/                       # Pytest automated test suite (39 tests)
│   ├── conftest.py              # In-memory SQLite fixtures & TestClient
│   ├── test_health.py
│   ├── test_inventory.py
│   ├── test_stock.py
│   ├── test_sales.py
│   ├── test_dashboard.py
│   ├── test_reports.py
│   └── test_ai.py               # Phase 5: Gemini intent, resolution, confirmation
├── requirements.txt
├── .env.example
└── README.md
```

---

## 3. Phase 5: Gemini AI Intelligence Engine

### Supported Natural Languages
- **Tamil (தமிழ் Script):** “5 கிலோ அரிசி இருப்பு சேர்”, “2 லிட்டர் எண்ணெய் விற்றுட்டேன்”, “இன்றைய விற்பனை எவ்வளவு?”
- **Tanglish (Tamil in English Letters):** “Innaiku 5 kilo rice stock add pannunga”, “3 kilo rice sale panniten”, “Sugar stock evlo irukku?”, “Innaiku sales evlo?”
- **English:** “Add 10 packets of biscuits”, “Sell 2 bottles of sunflower oil”
- **Mixed Retail Colloquialisms:** “Customer-ku 2 oil bottle kuduthuten”, “Sugar 20 kilo vandhirukku”

### Supported Intent Categories
1. `ADD_STOCK`: Merchant received wholesale inventory delivery.
2. `SELL_PRODUCT`: Merchant sold products to a customer.
3. `CHECK_STOCK`: Merchant queries the current stock level of a product.
4. `LOW_STOCK_QUERY`: Merchant queries all products running below their minimum stock threshold.
5. `SALES_REPORT`: Merchant queries daily/weekly revenue and order counts.
6. `PRODUCT_SALES_REPORT`: Merchant queries sales for a specific product or best sellers.
7. `INVENTORY_REPORT`: Merchant queries overall inventory valuation and margins.
8. `CREATE_PRODUCT`: Merchant requests registering a new product item.
9. `UNKNOWN`: Unintelligible speech or unrelated requests.

### Two-Step Confirmation Workflow
To ensure that LLM models **never directly modify the database**, Phase 5 enforces a strict safety boundary:

```text
User speaks or types command
        ↓
Gemini extracts structured intent (IntentCategory, entities, confidence)
        ↓
Pydantic validates schema (quantities > 0, unit normalization)
        ↓
Product Resolver matches against SQLite catalog (exact, Tanglish/Tamil synonyms)
        ↓
Backend validates business rules (stock availability, DB pricing)
        ↓
Backend issues a temporary secure action token (UUID with TTL)
        ↓
Frontend displays Confirmation Preview (Action, Product, Quantity, Current & Projected Stock)
        ↓
User confirms or cancels:
    - POST /api/ai/confirm  → Revalidates stock in real-time, executes transaction atomically
    - POST /api/ai/cancel   → Safely discards token without any database modification
```

### AI Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/ai/status` | Reports Gemini configuration status, enabled state, and model name (no keys leaked) |
| `POST` | `/api/ai/interpret` | Extracts intent, resolves product from SQLite, and generates confirmation preview |
| `POST` | `/api/ai/confirm` | Executes a validated pending action atomically against SQLite |
| `POST` | `/api/ai/cancel` | Cancels and discards a pending action token |

---

## 4. Environment Variables Configuration

Create a `.env` file in the `backend/` directory (or use `.env.example` as a template):

```env
# Application Settings
PROJECT_NAME="TamilVoice Kirana AI"
VERSION="1.0.0"
API_PREFIX="/api"
DATABASE_URL="sqlite:///./kirana_ai.db"
TIMEZONE="Asia/Kolkata"
DEBUG=true

# Google Gemini API Configuration (Official Google GenAI SDK)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_ENABLED=true
GEMINI_TIMEOUT_SECONDS=15.0
```

> **Security Note:** `.env` is listed in `.gitignore` and must never be committed to source control. If `GEMINI_API_KEY` is not configured, the frontend gracefully operates in client-side Demo Mode.

---

## 5. Running the Backend Locally (Windows PowerShell)

```powershell
# Navigate to backend directory
cd backend

# Activate virtual environment if present
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python -m alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive documentation will be available at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 6. Running Automated Tests

Run the full automated test suite (39 tests, including Phase 4 CRUD and Phase 5 Gemini intent extraction):

```powershell
python -m pytest backend/tests -v
```

All AI tests use offline mocked responses and do not consume Gemini API quota or require live network access.
