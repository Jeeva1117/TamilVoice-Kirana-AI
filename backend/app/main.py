"""TamilVoice Kirana AI - FastAPI Application Entry Point."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.database_seeder import seed_database
from backend.app.routers import (
    health_router,
    inventory_router,
    stock_router,
    sales_router,
    customers_router,
    dashboard_router,
    reports_router,
    voice_router,
    ai_router,
    settings_router,
    system_test_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown events."""
    # Ensure all tables exist in SQLite database
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-grade FastAPI backend with SQLite for Indian Kirana shop management.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware configured for Local Development & Vercel Production Domains
cors_list = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]
if settings.FRONTEND_URL and settings.FRONTEND_URL.strip():
    clean_fe = settings.FRONTEND_URL.strip().rstrip("/")
    if clean_fe not in cors_list:
        cors_list.append(clean_fe)

if isinstance(settings.CORS_ORIGINS, list):
    for o in settings.CORS_ORIGINS:
        if o and o not in cors_list and o != "*":
            cors_list.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_list,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount API Routers under /api
api_prefix = settings.API_PREFIX

# Mount health router at both root (/health) for cloud monitoring/Render and under /api (/api/health)
app.include_router(health_router, prefix="")
app.include_router(health_router, prefix=api_prefix)

app.include_router(inventory_router, prefix=api_prefix)
app.include_router(stock_router, prefix=api_prefix)
app.include_router(sales_router, prefix=api_prefix)
app.include_router(customers_router, prefix=api_prefix)
app.include_router(dashboard_router, prefix=api_prefix)
app.include_router(reports_router, prefix=api_prefix)
app.include_router(voice_router, prefix=api_prefix)
app.include_router(ai_router, prefix=api_prefix)
app.include_router(settings_router, prefix=api_prefix)
app.include_router(system_test_router, prefix=api_prefix)


@app.get("/api")
def root():
    """Root info endpoint."""
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs": "/docs",
        "health": f"{settings.API_PREFIX}/health",
    }


# Mount frontend static files to serve the complete application seamlessly
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )


