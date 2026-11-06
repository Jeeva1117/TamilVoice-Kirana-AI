"""TamilVoice Kirana AI - FastAPI Application Entry Point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown events."""
    # Ensure all tables exist in SQLite
    Base.metadata.create_all(bind=engine)

    # Seed initial Kirana catalog if fresh database
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-grade FastAPI backend with SQLite for Indian Kirana shop management.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits local development on port 3000 / 8000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers under /api
api_prefix = settings.API_PREFIX
app.include_router(health_router, prefix=api_prefix)
app.include_router(inventory_router, prefix=api_prefix)
app.include_router(stock_router, prefix=api_prefix)
app.include_router(sales_router, prefix=api_prefix)
app.include_router(customers_router, prefix=api_prefix)
app.include_router(dashboard_router, prefix=api_prefix)
app.include_router(reports_router, prefix=api_prefix)
app.include_router(voice_router, prefix=api_prefix)
app.include_router(ai_router, prefix=api_prefix)


@app.get("/")
def root():
    """Root info endpoint."""
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs": "/docs",
        "health": f"{settings.API_PREFIX}/health",
    }
