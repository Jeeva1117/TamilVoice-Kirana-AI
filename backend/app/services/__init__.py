"""Services Package."""
from backend.app.services.inventory_service import (
    get_products,
    get_product_by_id,
    get_product_by_sku,
    create_product,
    update_product,
    delete_product,
    get_categories,
)
from backend.app.services.stock_service import (
    adjust_stock,
    get_product_movements,
    get_all_movements,
)
from backend.app.services.sales_service import (
    create_sale,
    get_sales,
    get_sale_by_id,
    get_sale_by_transaction_id,
)
from backend.app.services.dashboard_service import (
    get_dashboard_summary,
)
from backend.app.services.reports_service import (
    get_daily_report,
    get_products_report,
    get_inventory_valuation,
)
from backend.app.services.product_resolver import (
    resolve_product,
    ResolutionStatus,
)
from backend.app.services.gemini_client import (
    gemini_client,
    GeminiError,
    GeminiNotConfiguredError,
)
from backend.app.services.ai_service import (
    interpret_user_command,
    confirm_pending_action,
    cancel_pending_action,
    pending_store,
)

from backend.app.services.gnani_stt_service import (
    gnani_stt_service,
    GnaniSTTService,
)
from backend.app.services.gnani_tts_service import (
    gnani_tts_service,
    GnaniTTSService,
)
from backend.app.services.voice_service import (
    voice_service,
    VoicePipelineService,
)

__all__ = [
    "get_products",
    "get_product_by_id",
    "get_product_by_sku",
    "create_product",
    "update_product",
    "delete_product",
    "get_categories",
    "adjust_stock",
    "get_product_movements",
    "get_all_movements",
    "create_sale",
    "get_sales",
    "get_sale_by_id",
    "get_sale_by_transaction_id",
    "get_dashboard_summary",
    "get_daily_report",
    "get_products_report",
    "get_inventory_valuation",
    "resolve_product",
    "ResolutionStatus",
    "gemini_client",
    "GeminiError",
    "GeminiNotConfiguredError",
    "interpret_user_command",
    "confirm_pending_action",
    "cancel_pending_action",
    "pending_store",
    "gnani_stt_service",
    "GnaniSTTService",
    "gnani_tts_service",
    "GnaniTTSService",
    "voice_service",
    "VoicePipelineService",
]
