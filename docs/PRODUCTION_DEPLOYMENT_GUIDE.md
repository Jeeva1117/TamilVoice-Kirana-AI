# TamilVoice Kirana AI — Production Deployment & Cloud Migration Guide

This guide details the complete production deployment architecture for **TamilVoice Kirana AI**:
- **Frontend:** Vercel (Static HTML, CSS, Vanilla JavaScript)
- **Backend:** Render (Python FastAPI, Uvicorn)
- **Production Database:** Supabase (Managed PostgreSQL)
- **Local Development:** SQLite (`kirana_ai.db`)
- **Speech-to-Text:** Gnani Prisma v2.5
- **Intent Understanding:** Google Gemini (`gemini-3.8-flash`)
- **Text-to-Speech:** Gnani Timbre v2.5

---

## 1. Architecture Overview

```
                      +-----------------------------+
                      |       Vercel Frontend       |
                      |   (HTML / CSS / Vanilla JS) |
                      +--------------+--------------+
                                     |
                         HTTPS Fetch | Web Audio API
                                     v
                      +-----------------------------+
                      |     Render Web Service      |
                      |   (FastAPI on Port $PORT)   |
                      +-------+--------------+------+
                              |              |
         SQLAlchemy / psycopg2|              | Official APIs
         (sslmode=require)    |              |
                              v              v
        +-----------------------+     +-----------------------+
        |  Supabase PostgreSQL  |     |  Gnani.ai & Google    |
        |  (Authoritative DB)   |     |  Prisma / Timbre / AI |
        +-----------------------+     +-----------------------+
```

---

## 2. Supabase PostgreSQL Setup & Data Migration

### Step 2.1: Obtain Connection String from Supabase
1. Create a new project in [Supabase](https://supabase.com).
2. Go to **Project Settings** -> **Database**.
3. Under **Connection string**, select **URI** (Direct connection on port `5432` or Transaction Pooler on port `6543`).
   Example:
   `postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require`

### Step 2.2: Migrate Local SQLite Records to Supabase
Run the automated migration tool from your local terminal:
```bash
python -m backend.app.migrate_sqlite_to_postgres --postgres-url "YOUR_SUPABASE_POSTGRES_URL"
```
What this tool does:
- Validates both SQLite and PostgreSQL connections.
- Automatically creates all tables and foreign keys in PostgreSQL via SQLAlchemy `Base.metadata.create_all`.
- Migrates records in foreign-key dependency order (`store_settings` -> `customers` -> `products` -> `sales` -> `sale_items` -> `stock_movements` -> `gnani_api_usage`).
- Resets PostgreSQL auto-increment sequences (`pg_get_serial_sequence`) so future inserts do not collide with migrated IDs.
- Audits and compares row counts between SQLite and PostgreSQL.

### Step 2.3: Verify PostgreSQL Health
```bash
python -m backend.app.test_postgres_connection --url "YOUR_SUPABASE_POSTGRES_URL"
```

---

## 3. Render FastAPI Backend Deployment

### Step 3.1: Connect GitHub Repository
1. Log in to [Render](https://render.com) and click **New +** -> **Web Service**.
2. Connect repository `https://github.com/Jeeva1117/TamilVoice-Kirana-AI`.

### Step 3.2: Configure Service Parameters
- **Name:** `tamilvoice-kirana-api`
- **Region:** Singapore / Mumbai (lowest latency to India)
- **Branch:** `main`
- **Root Directory:** `.`
- **Runtime:** `Python`
- **Build Command:** `pip install -r backend/requirements.txt`
- **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`

### Step 3.3: Environment Variables
Configure the following in the Render dashboard:
| Variable Name | Example / Description |
| :--- | :--- |
| `DATABASE_URL` | Supabase PostgreSQL connection URI (`postgresql://...`) |
| `ENVIRONMENT` | `production` |
| `GEMINI_API_KEY` | Google Gemini API Key |
| `GEMINI_MODEL` | `gemini-3.8-flash` |
| `GNANI_API_KEY` | Unified Gnani.ai API Key (powers Prisma STT & Timbre TTS) |
| `FRONTEND_URL` | Deployed Vercel frontend URL (e.g. `https://tamilvoice-kirana.vercel.app`) |
| `TIMEZONE` | `Asia/Kolkata` |

### Step 3.4: Verify Deployed Health
Once deployed, probe the health endpoint:
```bash
curl https://your-service.onrender.com/api/health
```
Expected response:
```json
{
  "status": "healthy",
  "service": "TamilVoice Kirana AI",
  "version": "1.0.0",
  "environment": "production",
  "database": "connected",
  "database_type": "postgresql",
  "timezone": "Asia/Kolkata"
}
```

---

## 4. Vercel Frontend Deployment

### Step 4.1: Deploy Static Site
1. Log in to [Vercel](https://vercel.com) and click **Add New...** -> **Project**.
2. Import `https://github.com/Jeeva1117/TamilVoice-Kirana-AI`.
3. In Project Settings:
   - **Framework Preset:** Other
   - **Root Directory:** `.`
   - **Output Directory:** `frontend`
4. Deploy.

### Step 4.2: Connect Frontend to Render Backend
Open `frontend/js/env.js` and set your Render URL:
```javascript
window.__API_BASE_URL__ = "https://your-service.onrender.com/api";
```
Alternatively, navigate to **Store Settings** in the UI and enter your backend URL in the **Backend API URL** field. It is saved in `localStorage` and persists across sessions.
