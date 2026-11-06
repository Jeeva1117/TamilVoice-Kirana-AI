"""Routers Package."""
from backend.app.routers.health import router as health_router
from backend.app.routers.inventory import router as inventory_router
from backend.app.routers.stock import router as stock_router
from backend.app.routers.sales import router as sales_router
from backend.app.routers.customers import router as customers_router
from backend.app.routers.dashboard import router as dashboard_router
from backend.app.routers.reports import router as reports_router
from backend.app.routers.voice import router as voice_router
from backend.app.routers.ai import router as ai_router
from backend.app.routers.settings import router as settings_router
from backend.app.routers.system_test import router as system_test_router

__all__ = [
    "health_router",
    "inventory_router",
    "stock_router",
    "sales_router",
    "customers_router",
    "dashboard_router",
    "reports_router",
    "voice_router",
    "ai_router",
    "settings_router",
    "system_test_router",
]
