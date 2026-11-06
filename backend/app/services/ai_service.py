"""AI Service: Intent interpretation, business rule verification, and safe two-step confirmation."""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.config import settings
from backend.app.models.product import Product
from backend.app.models.sale import Sale
from backend.app.models.sale_item import SaleItem
from backend.app.schemas.ai import (
    CommandIntent,
    IntentCategory,
    InterpretResponse,
    ConfirmationPreview,
    ConfirmActionResponse,
    CancelActionResponse,
    ResolvedProduct,
)
from backend.app.schemas.stock import StockAdjustmentType
from backend.app.schemas.sale import SaleCreate, SaleItemCreate
from backend.app.services.gemini_client import (
    gemini_client,
    GeminiNotConfiguredError,
    GeminiError,
)
from backend.app.services.product_resolver import (
    resolve_product,
    ResolutionStatus,
    to_resolved_schema,
)
from backend.app.services import stock_service, sales_service, dashboard_service

logger = logging.getLogger(__name__)


class PendingAction:
    """Represents a validated pending transaction awaiting merchant confirmation."""

    def __init__(
        self,
        action_id: str,
        action: str,  # "ADD_STOCK" or "SELL_PRODUCT"
        product_id: int,
        product_name: str,
        product_name_ta: Optional[str],
        quantity: float,
        unit: str,
        current_stock: float,
        projected_stock: float,
        unit_price: Optional[float] = None,
        estimated_total: Optional[float] = None,
        payment_method: str = "CASH",
        ttl_minutes: int = 10,
    ):
        self.action_id = action_id
        self.action = action
        self.product_id = product_id
        self.product_name = product_name
        self.product_name_ta = product_name_ta
        self.quantity = quantity
        self.unit = unit
        self.current_stock = current_stock
        self.projected_stock = projected_stock
        self.unit_price = unit_price
        self.estimated_total = estimated_total
        self.payment_method = payment_method
        self.created_at = datetime.now(timezone.utc)
        self.expires_at = self.created_at + timedelta(minutes=ttl_minutes)

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at


class PendingActionStore:
    """Thread-safe in-memory store for pending confirmations with expiration."""

    def __init__(self):
        self._actions: Dict[str, PendingAction] = {}

    def save(self, action: PendingAction):
        self._cleanup_expired()
        self._actions[action.action_id] = action

    def get(self, action_id: str) -> Optional[PendingAction]:
        self._cleanup_expired()
        action = self._actions.get(action_id)
        if action and action.is_expired:
            self._actions.pop(action_id, None)
            return None
        return action

    def pop(self, action_id: str) -> Optional[PendingAction]:
        self._cleanup_expired()
        action = self._actions.pop(action_id, None)
        if action and action.is_expired:
            return None
        return action

    def remove(self, action_id: str) -> bool:
        return self._actions.pop(action_id, None) is not None

    def _cleanup_expired(self):
        now = datetime.now(timezone.utc)
        expired_keys = [k for k, v in self._actions.items() if v.expires_at < now]
        for k in expired_keys:
            self._actions.pop(k, None)


pending_store = PendingActionStore()


async def interpret_user_command(db: Session, text: str) -> InterpretResponse:
    """
    Orchestrate speech command interpretation:
    1. Call Gemini to extract structured intent and entities
    2. Check clarification requirements
    3. Resolve product against SQLite catalog
    4. Execute business validations (stock level, pricing, unit compatibility)
    5. Prepare confirmation preview without altering the database
    """
    if not settings.is_gemini_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Gemini API is not configured or disabled. "
                "Please set GEMINI_API_KEY in your .env file to enable live AI command extraction."
            )
        )

    try:
        intent = await gemini_client.generate_intent_async(text)
    except GeminiNotConfiguredError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except GeminiError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    # If Gemini explicitly flagged missing parameters or unknown intent
    if intent.requires_clarification:
        return InterpretResponse(
            success=True,
            intent=intent,
            requires_confirmation=False,
            message=intent.clarification_question or "Could you clarify your command?",
            message_ta="தயவுசெய்து உங்கள் கோரிக்கையை விளக்கமாக கூறவும்."
        )

    # =========================================================================
    # Intent: ADD_STOCK or SELL_PRODUCT (Consequential mutations requiring confirmation)
    # =========================================================================
    if intent.intent in (IntentCategory.ADD_STOCK, IntentCategory.SELL_PRODUCT):
        product_query = intent.entities.product_name
        qty = intent.entities.quantity

        if qty is None or qty <= 0:
            intent.requires_clarification = True
            action_word = "add" if intent.intent == IntentCategory.ADD_STOCK else "sell"
            question = f"How much {product_query or 'stock'} should I {action_word}?"
            intent.clarification_question = question
            return InterpretResponse(
                success=True,
                intent=intent,
                requires_confirmation=False,
                message=question,
                message_ta=f"எவ்வளவு அளவு {action_word} செய்ய வேண்டும்?"
            )

        res_status, resolved_prod, candidates = resolve_product(db, product_query)

        if res_status == ResolutionStatus.NO_MATCH:
            return InterpretResponse(
                success=True,
                intent=intent,
                requires_confirmation=False,
                message=(
                    f"Product '{product_query}' not found in inventory catalog. "
                    "Would you like to register this as a new product?"
                ),
                message_ta=f"'{product_query}' இருப்பு பட்டியலில் இல்லை. புதிய பொருளாக சேர்க்க வேண்டுமா?"
            )

        if res_status == ResolutionStatus.MULTIPLE_MATCHES:
            cand_names = ", ".join(p.name for p in candidates)
            return InterpretResponse(
                success=True,
                intent=intent,
                candidate_products=candidates,
                requires_confirmation=False,
                message=f"Multiple products matched '{product_query}': {cand_names}. Which one did you mean?",
                message_ta=f"பொருத்தமான பல பொருட்கள் உள்ளன ({cand_names}). சரியான பொருளை தேர்ந்தெடுக்கவும்."
            )

        # Single matched product from SQLite
        db_product = db.query(Product).filter(Product.id == resolved_prod.id, Product.is_active == True).first()
        if not db_product:
            raise HTTPException(status_code=404, detail=f"Product '{resolved_prod.name}' not found.")

        current_stock = db_product.quantity
        unit = intent.entities.unit or db_product.unit
        action_name = "ADD_STOCK" if intent.intent == IntentCategory.ADD_STOCK else "SELL_PRODUCT"

        # Validate sale stock availability
        if intent.intent == IntentCategory.SELL_PRODUCT:
            if current_stock < qty:
                return InterpretResponse(
                    success=False,
                    intent=intent,
                    resolved_product=resolved_prod,
                    requires_confirmation=False,
                    message=(
                        f"Insufficient stock for '{db_product.name}'. "
                        f"Current stock: {current_stock} {db_product.unit}, requested: {qty} {unit}."
                    ),
                    message_ta=(
                        f"'{db_product.name}' போதுமான இருப்பு இல்லை! "
                        f"தற்போது {current_stock} {db_product.unit} மட்டுமே உள்ளது."
                    )
                )

            projected_stock = round(current_stock - qty, 3)
            unit_price = round(db_product.selling_price, 2)
            estimated_total = round(qty * unit_price, 2)
        else:
            projected_stock = round(current_stock + qty, 3)
            unit_price = round(db_product.purchase_price, 2)
            estimated_total = None

        # Build secure pending confirmation
        action_id = str(uuid.uuid4())
        payment_method = (intent.entities.payment_method or "CASH").upper()

        pending_action = PendingAction(
            action_id=action_id,
            action=action_name,
            product_id=db_product.id,
            product_name=db_product.name,
            product_name_ta=db_product.name_ta,
            quantity=qty,
            unit=unit,
            current_stock=current_stock,
            projected_stock=projected_stock,
            unit_price=unit_price,
            estimated_total=estimated_total,
            payment_method=payment_method,
        )
        pending_store.save(pending_action)

        preview = ConfirmationPreview(
            action_id=action_id,
            action=action_name,
            product_id=db_product.id,
            product_name=db_product.name,
            product_name_ta=db_product.name_ta,
            quantity=qty,
            unit=unit,
            current_stock=current_stock,
            projected_stock=projected_stock,
            unit_price=unit_price,
            estimated_total=estimated_total,
            payment_method=payment_method,
            expires_at=pending_action.expires_at,
        )

        if action_name == "ADD_STOCK":
            msg = f"Ready to add {qty} {unit} of {db_product.name}. Stock will increase from {current_stock} to {projected_stock} {unit}."
            msg_ta = f"{db_product.name_ta or db_product.name} {qty} {unit} சேர்க்க தயார். இருப்பு {current_stock}-ல் இருந்து {projected_stock}-ஆக மாறும்."
        else:
            msg = f"Ready to record sale of {qty} {unit} of {db_product.name} for ₹{estimated_total}. Remaining stock: {projected_stock} {unit}."
            msg_ta = f"{db_product.name_ta or db_product.name} {qty} {unit} விற்பனை (₹{estimated_total}) பதிவு செய்ய தயார். மீதி இருப்பு: {projected_stock} {unit}."

        return InterpretResponse(
            success=True,
            intent=intent,
            resolved_product=resolved_prod,
            requires_confirmation=True,
            confirmation_preview=preview,
            message=msg,
            message_ta=msg_ta
        )

    # =========================================================================
    # Intent: CHECK_STOCK (Read-only inquiry)
    # =========================================================================
    if intent.intent == IntentCategory.CHECK_STOCK:
        product_query = intent.entities.product_name
        if not product_query:
            return InterpretResponse(
                success=True,
                intent=intent,
                requires_confirmation=False,
                message="Which product's stock would you like to check?",
                message_ta="எந்த பொருளின் இருப்பை சரிபார்க்க வேண்டும்?"
            )

        res_status, resolved_prod, candidates = resolve_product(db, product_query)

        if res_status == ResolutionStatus.MATCH and resolved_prod:
            status_text = "Out of Stock" if resolved_prod.is_out_of_stock else ("Low Stock" if resolved_prod.is_low_stock else "In Stock")
            msg = f"{resolved_prod.name}: Current stock is {resolved_prod.current_stock} {resolved_prod.unit} ({status_text})."
            msg_ta = f"{resolved_prod.name_ta or resolved_prod.name}: தற்போது {resolved_prod.current_stock} {resolved_prod.unit} இருப்பில் உள்ளது."
            return InterpretResponse(
                success=True,
                intent=intent,
                resolved_product=resolved_prod,
                requires_confirmation=False,
                query_result={
                    "product_id": resolved_prod.id,
                    "name": resolved_prod.name,
                    "stock": resolved_prod.current_stock,
                    "unit": resolved_prod.unit,
                    "status": resolved_prod.is_low_stock or resolved_prod.is_out_of_stock,
                },
                message=msg,
                message_ta=msg_ta
            )
        elif res_status == ResolutionStatus.MULTIPLE_MATCHES:
            return InterpretResponse(
                success=True,
                intent=intent,
                candidate_products=candidates,
                requires_confirmation=False,
                message=f"Found multiple products matching '{product_query}'. Which one would you like to inspect?",
                message_ta=f"'{product_query}' பெயரில் பல பொருட்கள் உள்ளன. எதை சரிபார்க்க வேண்டும்?"
            )
        else:
            return InterpretResponse(
                success=True,
                intent=intent,
                requires_confirmation=False,
                message=f"Product '{product_query}' is not in your store catalog.",
                message_ta=f"'{product_query}' இருப்பு பட்டியலில் இல்லை."
            )

    # =========================================================================
    # Intent: LOW_STOCK_QUERY
    # =========================================================================
    if intent.intent == IntentCategory.LOW_STOCK_QUERY:
        low_stock_prods = (
            db.query(Product)
            .filter(Product.is_active == True, Product.quantity <= Product.minimum_stock_level)
            .all()
        )
        count = len(low_stock_prods)
        names = ", ".join(f"{p.name} ({p.quantity} {p.unit})" for p in low_stock_prods[:5])
        if count == 0:
            msg = "All products have adequate stock levels. No low stock alerts right now."
            msg_ta = "அனைத்து பொருட்களும் போதுமான இருப்பில் உள்ளன."
        else:
            msg = f"{count} products need reordering: {names}."
            msg_ta = f"{count} பொருட்கள் குறைந்த இருப்பில் உள்ளன: {names}."

        return InterpretResponse(
            success=True,
            intent=intent,
            requires_confirmation=False,
            query_result={"low_stock_count": count, "items": [p.name for p in low_stock_prods]},
            message=msg,
            message_ta=msg_ta
        )

    # =========================================================================
    # Intent: SALES_REPORT
    # =========================================================================
    if intent.intent == IntentCategory.SALES_REPORT:
        dash = dashboard_service.get_dashboard_summary(db)
        kpi = dash.kpis
        msg = f"Today's total sales: ₹{kpi.today_sales:,.2f} across {kpi.today_orders} bills."
        msg_ta = f"இன்றைய விற்பனை: ₹{kpi.today_sales:,.2f} ({kpi.today_orders} பில்கள்)."
        return InterpretResponse(
            success=True,
            intent=intent,
            requires_confirmation=False,
            query_result={"today_sales": kpi.today_sales, "today_orders": kpi.today_orders},
            message=msg,
            message_ta=msg_ta
        )

    # =========================================================================
    # Intent: INVENTORY_REPORT
    # =========================================================================
    if intent.intent == IntentCategory.INVENTORY_REPORT:
        active_products = db.query(Product).filter(Product.is_active == True).all()
        total_value = sum(p.quantity * p.purchase_price for p in active_products)
        total_items = len(active_products)
        msg = f"Total inventory valuation is ₹{total_value:,.2f} across {total_items} catalog items."
        msg_ta = f"மொத்த இருப்பு மதிப்பு: ₹{total_value:,.2f} ({total_items} பொருட்கள்)."
        return InterpretResponse(
            success=True,
            intent=intent,
            requires_confirmation=False,
            query_result={"total_inventory_value": total_value, "total_products": total_items},
            message=msg,
            message_ta=msg_ta
        )

    # Fallback for other queries
    return InterpretResponse(
        success=True,
        intent=intent,
        requires_confirmation=False,
        message="Command parsed. How else can I assist your store?",
        message_ta="வணக்கம்! வேறு என்ன உதவி வேண்டும்?"
    )


def confirm_pending_action(db: Session, action_id: str) -> ConfirmActionResponse:
    """
    Execute a previously validated pending action:
    - Atomically re-validates stock and database constraints
    - Executes via stock_service or sales_service
    - Never executes twice (pops from store immediately)
    """
    action = pending_store.pop(action_id)
    if not action:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation session expired or action already executed. Please repeat your command."
        )

    # Re-fetch product from database with current lock/snapshot
    product = db.query(Product).filter(Product.id == action.product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {action.product_id} is no longer active."
        )

    prev_stock = product.quantity

    if action.action == "ADD_STOCK":
        result = stock_service.adjust_stock(
            db=db,
            product_id=product.id,
            adjustment_type=StockAdjustmentType.ADD,
            quantity=action.quantity,
            reason="Voice command confirmed by merchant",
            reference_id=f"AI-{action.action_id[:8]}"
        )
        msg = f"Stock updated successfully: {product.name} is now {result.new_quantity} {product.unit}."
        msg_ta = f"வெற்றிகரமாக சரக்கு சேர்க்கப்பட்டது! {product.name_ta or product.name} தற்போது {result.new_quantity} {product.unit} உள்ளது."

        return ConfirmActionResponse(
            success=True,
            action="ADD_STOCK",
            transaction_id=f"AI-{action.action_id[:8]}",
            product_name=product.name,
            previous_stock=prev_stock,
            new_stock=result.new_quantity,
            total_amount=None,
            message=msg,
            message_ta=msg_ta
        )

    elif action.action == "SELL_PRODUCT":
        # Final real-time stock guard
        if product.quantity < action.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for '{product.name}'. Available: {product.quantity} {product.unit}."
            )

        sale_in = SaleCreate(
            items=[SaleItemCreate(product_id=product.id, quantity=action.quantity)],
            payment_method=action.payment_method or "CASH",
            notes="Voice sale transaction confirmed by merchant"
        )
        sale = sales_service.create_sale(db=db, sale_in=sale_in)

        # Refresh product to get updated stock
        db.refresh(product)
        msg = f"Sale recorded! Bill {sale.transaction_id} for ₹{sale.total_amount:.2f}. Remaining {product.name} stock: {product.quantity} {product.unit}."
        msg_ta = f"விற்பனை பதிவு செய்யப்பட்டது! பில் எண் {sale.transaction_id}, தொகை ₹{sale.total_amount:.2f}. மீதி இருப்பு: {product.quantity} {product.unit}."

        return ConfirmActionResponse(
            success=True,
            action="SELL_PRODUCT",
            transaction_id=sale.transaction_id,
            product_name=product.name,
            previous_stock=prev_stock,
            new_stock=product.quantity,
            total_amount=sale.total_amount,
            message=msg,
            message_ta=msg_ta
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported action type: {action.action}"
    )


def cancel_pending_action(action_id: str) -> CancelActionResponse:
    """Safely cancel and discard a pending action without altering the database."""
    removed = pending_store.remove(action_id)
    if removed:
        return CancelActionResponse(
            success=True,
            message="Action was cancelled. No changes were made to store inventory or sales."
        )
    return CancelActionResponse(
        success=True,
        message="Action was already expired or not found. No changes were made."
    )
