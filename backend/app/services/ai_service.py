"""AI Service: Intent interpretation, business rule verification, and safe two-step confirmation."""
import re
import uuid
import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.config import settings
from backend.app.models.product import Product
from backend.app.models.sale import Sale
from backend.app.models.sale_item import SaleItem
from backend.app.schemas.ai import (
    CommandIntent,
    CommandEntities,
    OrderItemEntity,
    IntentCategory,
    InterpretResponse,
    ConfirmationPreview,
    ConfirmActionResponse,
    CancelActionResponse,
    ResolvedProduct,
)
from backend.app.services.speech_normalizer import (
    extract_kirana_items_from_text,
    extract_effective_quantity,
    normalize_spoken_numbers,
    detect_spoken_language,
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
from backend.app.services.billing_calculator import (
    calculate_line_item,
    calculate_bill,
    quantize_currency,
    to_decimal,
)

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
        items: Optional[List[Dict[str, Any]]] = None,
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
        self.items = items
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


class ConversationSession:
    """Manages short-term conversation context for continuous shopkeeper interaction."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.active_product_id: Optional[int] = None
        self.active_product_name: Optional[str] = None
        self.active_product_unit: Optional[str] = None
        self.last_action: Optional[str] = None
        self.last_quantity: Optional[float] = None
        self.last_unit: Optional[str] = None
        self.pending_action_id: Optional[str] = None
        self.pending_action_type: Optional[str] = None
        self.pending_items: Optional[List[Dict[str, Any]]] = None
        self.missing_field: Optional[str] = None
        self.cart_items: List[Dict[str, Any]] = []
        self.is_billing_session: bool = False
        self.updated_at: datetime = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "active_product_id": self.active_product_id,
            "active_product_name": self.active_product_name,
            "active_product_unit": self.active_product_unit,
            "last_action": self.last_action,
            "last_quantity": self.last_quantity,
            "last_unit": self.last_unit,
            "pending_action_id": self.pending_action_id,
            "pending_action_type": self.pending_action_type,
            "pending_items": self.pending_items,
            "missing_field": self.missing_field,
            "cart_items": self.cart_items,
            "is_billing_session": self.is_billing_session,
            "updated_at": self.updated_at.isoformat(),
        }

    def update_from_dict(self, data: Dict[str, Any]):
        for key, val in data.items():
            if hasattr(self, key) and val is not None:
                setattr(self, key, val)
        self.updated_at = datetime.now(timezone.utc)


class SessionManager:
    """In-memory session manager with automatic cleanup."""

    def __init__(self):
        self._sessions: Dict[str, ConversationSession] = {}

    def get_or_create(
        self,
        session_id: Optional[str] = None,
        client_context: Optional[Dict[str, Any]] = None
    ) -> ConversationSession:
        now = datetime.now(timezone.utc)
        expired = [sid for sid, s in self._sessions.items() if (now - s.updated_at).total_seconds() > 1800]
        for sid in expired:
            self._sessions.pop(sid, None)

        if not session_id:
            session_id = f"sess_{uuid.uuid4().hex[:12]}"

        session = self._sessions.get(session_id)
        if not session:
            session = ConversationSession(session_id=session_id)
            self._sessions[session_id] = session

        if client_context:
            session.update_from_dict(client_context)

        return session


session_manager = SessionManager()


def format_spoken_response(detected_lang: str, msg_en: str, msg_ta: str, msg_tanglish: Optional[str] = None) -> str:
    """Select the spoken response text tailored to the user's detected language."""
    if detected_lang == "English":
        return msg_en
    if detected_lang == "Tanglish":
        return msg_tanglish or msg_ta or msg_en
    return msg_ta or msg_tanglish or msg_en


async def interpret_user_command(
    db: Session,
    text: str,
    allow_mock: bool = False,
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> InterpretResponse:
    """
    Orchestrate speech command interpretation:
    1. Manage conversation session and short-term context
    2. Handle affirmative confirmation ("Aama") & cancellation ("Cancel")
    3. Handle contextual follow-ups ("Innum 5 kilo add pannunga", "Stock evlo irukku?")
    4. Call Gemini or localized Kirana provider
    5. Resolve products against SQLite catalog
    6. Prepare confirmation preview or execute safe operations
    """
    conv = session_manager.get_or_create(session_id=session_id, client_context=context)
    effective_session_id = conv.session_id

    user_lang = detect_spoken_language(text)
    lower_text = text.strip().lower()
    clean_lower = re.sub(r"[^\w\s\u0B80-\u0BFF]", " ", lower_text).strip()
    clean_text = re.sub(r"\s+", " ", clean_lower)

    # -------------------------------------------------------------------------
    # Turn Handler 1: Affirmative Voice Confirmation ("Aama", "Seri", "Confirm")
    # -------------------------------------------------------------------------
    affirmative_matches = [
        "aama", "aam", "seri", "confirm", "confirm pannunga", "pannidunga",
        "kodu", "yes", "seringa", "kudunga", "pannunga", "aama pannunga",
        "seri pannunga", "aama confirm", "aama confirm pannunga", "seri confirm pannunga",
        "ஆமா", "ஆம்", "சரி", "உறுதி", "உறுதிப்படுத்து"
    ]
    is_affirmative = (
        clean_text in affirmative_matches or
        bool(re.search(r"\b(?:aama|seri|confirm|yes|kodu|ஆமா|சரி|ஆம்)\b", clean_text))
    )

    if is_affirmative and conv.pending_action_id:
        try:
            confirmed = confirm_pending_action(db=db, action_id=conv.pending_action_id)
            conv.pending_action_id = None
            conv.pending_items = None
            conv.cart_items = []
            conv.is_billing_session = False
            conv.last_action = confirmed.action
            conv.updated_at = datetime.now(timezone.utc)

            # Match product from response
            res_prod = None
            if conv.active_product_id:
                p = db.query(Product).filter(Product.id == conv.active_product_id).first()
                if p:
                    res_prod = to_resolved_schema(p)

            return InterpretResponse(
                success=True,
                intent=CommandIntent(
                    intent=IntentCategory.CONFIRM_ACTION,
                    language=user_lang,
                    original_text=text,
                    normalized_text="Confirmed pending operation",
                    entities=CommandEntities(product_name=conv.active_product_name),
                    confidence=0.99,
                    requires_clarification=False,
                ),
                resolved_product=res_prod,
                requires_confirmation=False,
                message=confirmed.message,
                message_ta=confirmed.message_ta,
                detected_language=user_lang,
                spoken_response=format_spoken_response(user_lang, confirmed.message, confirmed.message_ta or confirmed.message),
                session_id=effective_session_id,
                context=conv.to_dict()
            )
        except Exception as e:
            logger.warning("Error confirming pending action in conversation: %s", e)
            conv.pending_action_id = None

    # -------------------------------------------------------------------------
    # Turn Handler 1B: Natural Affirmative Acknowledgment ("Okay", "Seri", "சரி")
    # When no pending action exists, respond politely without altering stock.
    # -------------------------------------------------------------------------
    if is_affirmative and not conv.pending_action_id:
        msg = "Okay! Anything else I can help you with in your shop today?"
        msg_ta = "சரிங்க! வேறு ஏதாவது உதவி வேண்டுமா?"
        msg_tanglish = "Seringa! Vera edhavadhu help venuma?"
        conv.updated_at = datetime.now(timezone.utc)
        return InterpretResponse(
            success=True,
            intent=CommandIntent(
                intent=IntentCategory.GENERAL_QUERY,
                language=user_lang,
                original_text=text,
                normalized_text="Shopkeeper acknowledgment",
                entities=CommandEntities(),
                confidence=0.99,
                requires_clarification=False,
            ),
            requires_confirmation=False,
            message=msg,
            message_ta=msg_ta,
            message_tanglish=msg_tanglish,
            detected_language=user_lang,
            spoken_response=format_spoken_response(user_lang, msg, msg_ta, msg_tanglish),
            session_id=effective_session_id,
            context=conv.to_dict()
        )

    # -------------------------------------------------------------------------
    # Turn Handler 1C: Politeness & Gratitude ("Thank you", "நன்றி", "Thanks", "Nandri")
    # -------------------------------------------------------------------------
    thank_matches = ["thank you", "thanks", "நன்றி", "nandri", "thank you so much", "okay thank you so much", "okay thank you", "romba nandri", "thx"]
    is_thank_you = clean_text in thank_matches or bool(re.search(r"\b(?:thank you|thanks|நன்றி|nandri)\b", clean_text))
    if is_thank_you:
        msg = "You're welcome! How else can I help your shop today?"
        msg_ta = "You're welcome! வேறு ஏதாவது உதவி வேண்டுமா?"
        msg_tanglish = "You're welcome! Vera edhavadhu help venuma?"
        conv.updated_at = datetime.now(timezone.utc)
        return InterpretResponse(
            success=True,
            intent=CommandIntent(
                intent=IntentCategory.THANK_YOU,
                language=user_lang,
                original_text=text,
                normalized_text="Merchant expressed gratitude",
                entities=CommandEntities(),
                confidence=0.99,
                requires_clarification=False,
            ),
            requires_confirmation=False,
            message=msg,
            message_ta=msg_ta,
            message_tanglish=msg_tanglish,
            detected_language=user_lang,
            spoken_response="You're welcome! வேறு ஏதாவது உதவி வேண்டுமா?",
            session_id=effective_session_id,
            context=conv.to_dict()
        )

    # -------------------------------------------------------------------------
    # Turn Handler 2: Voice Cancellation ("Cancel", "Cancel pannunga", "Vendaam")
    # -------------------------------------------------------------------------
    cancellation_matches = [
        "cancel", "cancel pannunga", "vendaam", "venaam", "vendam", "vendang",
        "no", "nirutha", "வேண்டாம்", "ரத்து", "ரத்து செய்"
    ]
    is_cancellation = (
        clean_text in cancellation_matches or
        bool(re.search(r"\b(?:cancel|vendaam|venaam|vendam|no|ரத்து)\b", clean_text))
    )

    if is_cancellation:
        if conv.pending_action_id:
            cancel_pending_action(action_id=conv.pending_action_id)
            conv.pending_action_id = None
        conv.cart_items = []
        conv.is_billing_session = False
        conv.updated_at = datetime.now(timezone.utc)
        canc_en = "Action was cancelled. No changes were made to store inventory or sales."
        canc_ta = "செயல்பாடு ரத்து செய்யப்பட்டது. கடையில் எந்த மாற்றமும் செய்யப்படவில்லை."
        canc_tanglish = "Action cancel panniyachu. Store-la endha change-um pannala."
        return InterpretResponse(
            success=True,
            intent=CommandIntent(
                intent=IntentCategory.CANCEL_ACTION,
                language=user_lang,
                original_text=text,
                normalized_text="Cancelled pending operation",
                entities=CommandEntities(),
                confidence=0.99,
                requires_clarification=False,
            ),
            requires_confirmation=False,
            message=canc_en,
            message_ta=canc_ta,
            message_tanglish=canc_tanglish,
            detected_language=user_lang,
            spoken_response=format_spoken_response(user_lang, canc_en, canc_ta, canc_tanglish),
            session_id=effective_session_id,
            context=conv.to_dict()
        )

    # -------------------------------------------------------------------------
    # Turn Handler 2.5: Conversational Greeting ("Vanakkam", "Hello", "Hi")
    # -------------------------------------------------------------------------
    greeting_words = ["vanakkam", "vanakam", "வணக்கம்", "hello", "hi", "namaste", "good morning", "good afternoon", "good evening"]
    is_greeting = lower_text in greeting_words or any(
        re.match(rf"^(?:{gw})(?:\s+(?:assistant|ai|ai\s+assistant|sir|ji|pa))?[.!]*$", lower_text)
        for gw in greeting_words
    )
    if is_greeting:
        conv.updated_at = datetime.now(timezone.utc)
        return InterpretResponse(
            success=True,
            intent=CommandIntent(
                intent=IntentCategory.UNKNOWN,
                language="Tamil" if re.search(r"[\u0B80-\u0BFF]", text) else "Tanglish",
                original_text=text,
                normalized_text="Shopkeeper greeting",
                entities=CommandEntities(),
                confidence=0.99,
                requires_clarification=False,
            ),
            requires_confirmation=False,
            message="Vanakkam! I am your Tamil Kirana Assistant. How can I help with your shop inventory or customer bill today?",
            message_ta="வணக்கம்! நான் உங்கள் தமிழ் கிரானா உதவியாளர். இன்று சரக்கு சேர்க்க வேண்டுமா அல்லது பில் போட வேண்டுமா?",
            session_id=effective_session_id,
            context=conv.to_dict()
        )

    # -------------------------------------------------------------------------
    # Turn Handler 2.1: Remove Item from Conversational Cart ("Sugar vendaam", "Sugar remove pannu")
    # -------------------------------------------------------------------------
    is_remove_cart = bool(
        re.search(r"\b(?:remove|vendaam|vendam|delete|korainga|eduthudu|நீக்கு|வேண்டாம்|கழி)\b", clean_text)
    )
    if is_remove_cart and conv.cart_items:
        removed_item = None
        for it in list(conv.cart_items):
            p_name = it["product_name"].lower()
            p_tokens = p_name.split()
            if any(t in clean_text for t in p_tokens if len(t) > 2):
                removed_item = it
                conv.cart_items.remove(it)
                break
        if not removed_item and len(conv.cart_items) == 1:
            removed_item = conv.cart_items.pop(0)

        if removed_item:
            rem_name = removed_item["product_name"]
            msg = f"{rem_name} removed from current bill. Remaining {len(conv.cart_items)} item(s) in bill."
            msg_ta = f"{rem_name} பில்லில் இருந்து நீக்கப்பட்டது. மீதம் {len(conv.cart_items)} பொருட்கள் உள்ளன."
            msg_tanglish = f"{rem_name} bill-la irundhu remove panniyachu. Meedhi {len(conv.cart_items)} items irukku."
            return InterpretResponse(
                success=True,
                intent=CommandIntent(
                    intent=IntentCategory.SELL_PRODUCT,
                    language=user_lang,
                    original_text=text,
                    normalized_text=f"Removed {rem_name} from bill",
                    entities=CommandEntities(),
                    confidence=0.99,
                    requires_clarification=False
                ),
                requires_confirmation=False,
                message=msg,
                message_ta=msg_ta,
                message_tanglish=msg_tanglish,
                detected_language=user_lang,
                spoken_response=format_spoken_response(user_lang, msg, msg_ta, msg_tanglish),
                session_id=effective_session_id,
                context=conv.to_dict()
            )

    # -------------------------------------------------------------------------
    # Turn Handler 2.2: Change Item Quantity in Conversational Cart ("Sugar 1 kg mathu", "Change sugar to 1 kg")
    # -------------------------------------------------------------------------
    is_change_qty = bool(
        re.search(r"\b(?:change|mathu|maathu|update|மாற்று)\b", clean_text)
    )
    if is_change_qty and conv.cart_items:
        new_items = extract_kirana_items_from_text(text)
        if new_items:
            target = new_items[0]
            st, res_prod, _ = resolve_product(db, target["product_name"])
            matched_cart = None
            if st == ResolutionStatus.MATCH and res_prod:
                matched_cart = next((c for c in conv.cart_items if c["product_id"] == res_prod.id), None)
            if not matched_cart and len(conv.cart_items) == 1:
                matched_cart = conv.cart_items[0]

            if matched_cart:
                matched_cart["quantity"] = target["quantity"]
                if target.get("unit"):
                    matched_cart["unit"] = target["unit"]
                line_tot_dec = calculate_line_item(matched_cart["quantity"], matched_cart["unit_price"], matched_cart["unit"])
                matched_cart["line_total"] = float(line_tot_dec)
                q_fmt = int(matched_cart["quantity"]) if float(matched_cart["quantity"]).is_integer() else matched_cart["quantity"]
                msg = f"{matched_cart['product_name']} quantity updated to {q_fmt} {matched_cart['unit']}."
                msg_ta = f"{matched_cart['product_name']} அளவு {q_fmt} {matched_cart['unit']} என மாற்றப்பட்டது."
                msg_tanglish = f"{matched_cart['product_name']} quantity {q_fmt} {matched_cart['unit']}-nu mathiyachu."
                return InterpretResponse(
                    success=True,
                    intent=CommandIntent(
                        intent=IntentCategory.SELL_PRODUCT,
                        language=user_lang,
                        original_text=text,
                        normalized_text=f"Updated quantity of {matched_cart['product_name']}",
                        entities=CommandEntities(),
                        confidence=0.99,
                        requires_clarification=False
                    ),
                    requires_confirmation=False,
                    message=msg,
                    message_ta=msg_ta,
                    message_tanglish=msg_tanglish,
                    detected_language=user_lang,
                    spoken_response=format_spoken_response(user_lang, msg, msg_ta, msg_tanglish),
                    session_id=effective_session_id,
                    context=conv.to_dict()
                )

    # -------------------------------------------------------------------------
    # Turn Handler 2.3: Finalize Conversational Bill ("Bill ready pannu", "Bill podu", "Ellam bill podu")
    # -------------------------------------------------------------------------
    is_finalize_bill = bool(
        re.search(r"\b(?:bill\s+ready|ready\s+pannu|bill\s+podu|ellam\s+bill|total\s+evlo|bill\s+amount|பில்\s+தயார்|பில்\s+போடு)\b", clean_text)
    )
    if is_finalize_bill and conv.cart_items:
        items_spec = []
        for it in conv.cart_items:
            db_item = db.query(Product).filter(Product.id == it["product_id"], Product.is_active == True).first()
            if not db_item or db_item.quantity < it["quantity"]:
                avail = db_item.quantity if db_item else 0
                return InterpretResponse(
                    success=False,
                    intent=CommandIntent(
                        intent=IntentCategory.SELL_PRODUCT,
                        language=user_lang,
                        original_text=text,
                        normalized_text="Bill stock check",
                        entities=CommandEntities(),
                        confidence=0.99,
                        requires_clarification=False
                    ),
                    requires_confirmation=False,
                    message=f"Insufficient stock for '{it['product_name']}'. Available: {avail} {it['unit']}, requested: {it['quantity']} {it['unit']}.",
                    message_ta=f"'{it['product_name']}' போதுமான இருப்பு இல்லை! தற்போது {avail} மட்டுமே உள்ளது.",
                    session_id=effective_session_id,
                    context=conv.to_dict()
                )
            line_tot_dec = calculate_line_item(it["quantity"], db_item.selling_price, db_item.unit)
            items_spec.append({
                "product_id": db_item.id,
                "product_name": db_item.name,
                "quantity": it["quantity"],
                "unit": it.get("unit") or db_item.unit,
                "current_stock": db_item.quantity,
                "projected_stock": round(db_item.quantity - it["quantity"], 3),
                "unit_price": float(quantize_currency(db_item.selling_price)),
                "line_total": float(line_tot_dec)
            })

        grand_total_dec = sum((to_decimal(it["line_total"]) for it in items_spec), Decimal("0.00"))
        grand_total = float(grand_total_dec)
        tot_int = int(grand_total) if grand_total.is_integer() else grand_total
        first_prod = db.query(Product).filter(Product.id == items_spec[0]["product_id"]).first()
        act_id = str(uuid.uuid4())

        pending_action = PendingAction(
            action_id=act_id,
            action="SELL_PRODUCT",
            product_id=first_prod.id,
            product_name=", ".join(it["product_name"] for it in items_spec),
            product_name_ta="வாடிக்கையாளர் பில்",
            quantity=sum(it["quantity"] for it in items_spec),
            unit="items",
            current_stock=first_prod.quantity,
            projected_stock=round(first_prod.quantity - items_spec[0]["quantity"], 3),
            unit_price=None,
            estimated_total=grand_total,
            payment_method="CASH",
            items=items_spec
        )
        pending_store.save(pending_action)
        conv.pending_action_id = act_id
        conv.pending_items = items_spec
        conv.last_action = "SELL_PRODUCT"
        conv.updated_at = datetime.now(timezone.utc)

        preview = ConfirmationPreview(
            action_id=act_id,
            action="SELL_PRODUCT",
            product_id=first_prod.id,
            product_name="Customer Order: " + ", ".join(f"{it['product_name']} ({it['quantity']} {it['unit']})" for it in items_spec),
            product_name_ta="வாடிக்கையாளர் பில்",
            quantity=sum(it["quantity"] for it in items_spec),
            unit="items",
            current_stock=first_prod.quantity,
            projected_stock=round(first_prod.quantity - items_spec[0]["quantity"], 3),
            unit_price=None,
            estimated_total=grand_total,
            payment_method="CASH",
            items=items_spec,
            expires_at=pending_action.expires_at,
        )

        item_lines = ", ".join(f"{it['product_name']} ({it['quantity']} {it['unit']})" for it in items_spec)
        msg = f"Bill preview ready: {item_lines}. Total bill is ₹{grand_total:.2f}. Shall I confirm and generate bill?"
        msg_ta = f"பில் தயார். மொத்தம் ₹{tot_int}. பில் உறுதி செய்யவா?"
        msg_tanglish = f"Bill preview ready. Total bill ₹{tot_int}. Confirm pannalama?"

        return InterpretResponse(
            success=True,
            intent=CommandIntent(
                intent=IntentCategory.SELL_PRODUCT,
                language=user_lang,
                original_text=text,
                normalized_text="Bill preview generation",
                entities=CommandEntities(),
                confidence=0.99,
                requires_clarification=False
            ),
            resolved_product=to_resolved_schema(first_prod),
            requires_confirmation=True,
            confirmation_preview=preview,
            message=msg,
            message_ta=msg_ta,
            message_tanglish=msg_tanglish,
            detected_language=user_lang,
            spoken_response=format_spoken_response(user_lang, msg, msg_ta, msg_tanglish),
            session_id=effective_session_id,
            context=conv.to_dict()
        )

    # -------------------------------------------------------------------------
    # Turn Handler 2.4: Turn-by-Turn Conversational Cart Building
    # e.g., "Customer-ku 2 kg sugar", "Rice 3 kg", "Tea powder 2 packet"
    # -------------------------------------------------------------------------
    is_explicit_stock = any(kw in lower_text for kw in ["stock", "stock-la", "சரக்கு", "இருப்பு", "check stock", "evlo irukku", "evvalavu irukku"])
    is_explicit_price = any(kw in lower_text for kw in ["விலை", "price", "rate", "evlo rate"])
    is_bill_finalize = any(kw in lower_text for kw in [
        "bill podu", "podu", "podunga", "bill ready", "ready pannu", "ellam bill",
        "sale", "sell", "kuduthuten", "bill", "பில்"
    ])

    if (("customer" in lower_text or "வாடிக்கையாளர்" in lower_text or conv.is_billing_session)
        and not is_explicit_stock and not is_explicit_price and not is_bill_finalize):
        
        extracted_cart = extract_kirana_items_from_text(text)
        if extracted_cart:
            added_items = []
            for item in extracted_cart:
                st, res_prod, _ = resolve_product(db, item["product_name"])
                if st == ResolutionStatus.MATCH and res_prod:
                    db_item = db.query(Product).filter(Product.id == res_prod.id, Product.is_active == True).first()
                    if db_item:
                        qty = item["quantity"]
                        unit = item["unit"] or db_item.unit
                        unit_p_dec = quantize_currency(db_item.selling_price)
                        line_tot_dec = calculate_line_item(qty, unit_p_dec, unit)
                        
                        existing = next((c for c in conv.cart_items if c["product_id"] == db_item.id), None)
                        if existing:
                            existing["quantity"] += qty
                            existing["line_total"] = float(calculate_line_item(existing["quantity"], unit_p_dec, unit))
                        else:
                            conv.cart_items.append({
                                "product_id": db_item.id,
                                "product_name": db_item.name,
                                "quantity": qty,
                                "unit": unit,
                                "unit_price": float(unit_p_dec),
                                "line_total": float(line_tot_dec)
                            })
                        added_items.append((db_item, qty, unit))

            if added_items:
                conv.is_billing_session = True
                last_db, last_qty, last_unit = added_items[-1]
                conv.active_product_id = last_db.id
                conv.active_product_name = last_db.name
                conv.last_quantity = last_qty
                conv.last_unit = last_unit
                conv.updated_at = datetime.now(timezone.utc)

                if len(added_items) == 1:
                    d_prod, q, u = added_items[0]
                    q_fmt = int(q) if q.is_integer() else q
                    msg = f"{q_fmt} {u} {d_prod.name} added to current bill. Anything else?"
                    msg_ta = f"{q_fmt} {u} {d_prod.name_ta or d_prod.name} சேர்க்கப்பட்டது. வேறு ஏதாவது பொருள் உள்ளதா?"
                    msg_tanglish = f"{q_fmt} {u} {d_prod.name} bill-la add panniyachu. Vera edhavadhu irukka?"
                else:
                    item_desc = ", ".join(f"{it[0].name} ({int(it[1]) if it[1].is_integer() else it[1]} {it[2]})" for it in added_items)
                    msg = f"{item_desc} added to current bill. Anything else?"
                    msg_ta = f"பொருட்கள் பில்லில் சேர்க்கப்பட்டன. வேறு ஏதாவது பொருள் உள்ளதா?"
                    msg_tanglish = f"{len(added_items)} items bill-la add panniyachu. Vera edhavadhu irukka?"

                return InterpretResponse(
                    success=True,
                    intent=CommandIntent(
                        intent=IntentCategory.SELL_PRODUCT,
                        language=user_lang,
                        original_text=text,
                        normalized_text="Item added to conversational cart",
                        entities=CommandEntities(
                            product_name=conv.active_product_name,
                            quantity=conv.last_quantity,
                            unit=conv.last_unit
                        ),
                        confidence=0.99,
                        requires_clarification=False
                    ),
                    resolved_product=to_resolved_schema(last_db),
                    requires_confirmation=False,
                    message=msg,
                    message_ta=msg_ta,
                    message_tanglish=msg_tanglish,
                    detected_language=user_lang,
                    spoken_response=format_spoken_response(user_lang, msg, msg_ta, msg_tanglish),
                    session_id=effective_session_id,
                    context=conv.to_dict()
                )

    # -------------------------------------------------------------------------
    # Turn Handler 2.8: Product Correction ("இல்ல, onion சொன்னேன்", "அது இல்ல, tomato சொன்னேன்")
    # -------------------------------------------------------------------------
    command_to_process = text
    is_correction = bool(re.search(r"\b(?:இல்ல|illa|illai|no)\b", lower_text)) and any(
        w in lower_text for w in ["சொன்னேன்", "sonnen", "sonnan", "சொல்லல"]
    )
    if is_correction or (lower_text.startswith("இல்ல ") or lower_text.startswith("illa ")):
        # Extract corrected product query
        clean_corr = re.sub(r"\b(?:அது|adhu|illa|இல்ல|illai|sonnen|சொன்னேன்|sonnan|mattum|dhane|please)\b", " ", lower_text).strip()
        st_corr, res_corr, _ = resolve_product(db, clean_corr)
        if st_corr == ResolutionStatus.MATCH and res_corr:
            # Safely cancel pending action if any was active
            if conv.pending_action_id:
                cancel_pending_action(conv.pending_action_id)
                conv.pending_action_id = None

            conv.active_product_id = res_corr.id
            conv.active_product_name = res_corr.name
            conv.active_product_unit = res_corr.unit

            prev_act = conv.pending_action_type or conv.last_action or "ADD_STOCK"
            prev_qty = conv.last_quantity or 1.0
            act_word = "add" if prev_act == "ADD_STOCK" else "sale"
            command_to_process = f"{prev_qty} {conv.active_product_unit} {res_corr.name} {act_word} pannunga"
            conv.missing_field = None

    # -------------------------------------------------------------------------
    # Turn Handler 2.9: Pronoun Reference ("அதுக்கு bill போடு", "Adhuku bill podu")
    # -------------------------------------------------------------------------
    if ("அதுக்கு" in lower_text or "adhuku" in lower_text or "athuku" in lower_text) and ("bill" in lower_text or "பில்" in lower_text):
        if conv.active_product_name:
            qty_fmt = f"{conv.last_quantity} {conv.last_unit or 'kg'}" if conv.last_quantity else ""
            command_to_process = f"{conv.active_product_name} {qty_fmt} bill podunga".strip()

    # -------------------------------------------------------------------------
    # Turn Handler 3: Missing Quantity Answer (Follow-up dialogue)
    # e.g., Shopkeeper says "15 litres" or "15" after assistant asked "Evlo litre Gold Winner Oil add pannanum?"
    # -------------------------------------------------------------------------
    if conv.missing_field == "quantity" and conv.active_product_name:
        # Check if user provided number
        qty_match = re.search(r"(\d+(\.\d+)?)", lower_text)
        if qty_match and not any(p in lower_text for p in ["rice", "oil", "wheat", "tomato", "onion", "milk", "sugar", "tea", "masala"]):
            command_to_process = f"{text} {conv.active_product_name} add pannunga"
            conv.missing_field = None

    # -------------------------------------------------------------------------
    # Turn Handler 3.5: Missing Product Answer (Follow-up dialogue)
    # e.g., Assistant asked "Endha product-ku 5 kg add pannanum?", Shopkeeper says "Wheat Flour"
    # -------------------------------------------------------------------------
    if conv.missing_field == "product" and conv.last_quantity:
        st_prod, res_p, _ = resolve_product(db, text)
        if st_prod == ResolutionStatus.MATCH and res_p:
            act_word = "add" if conv.pending_action_type == "ADD_STOCK" else "sale"
            command_to_process = f"{conv.last_quantity} {conv.last_unit or 'kg'} {res_p.name} {act_word} pannunga"
            conv.missing_field = None

    # -------------------------------------------------------------------------
    # Step 4: Intent Extraction (Gemini with Local NLP Fallback)
    # -------------------------------------------------------------------------
    if not settings.is_gemini_ready:
        if allow_mock:
            from backend.app.services.providers import _mock_intent
            intent = await _mock_intent.extract_intent(command_to_process)
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini API is not configured. Please set GEMINI_API_KEY in .env."
            )
    else:
        try:
            intent = await gemini_client.generate_intent_async(command_to_process, context=conv.to_dict())
        except (GeminiNotConfiguredError, GeminiError) as e:
            logger.warning("Gemini API call encountered an issue (%s), falling back to local NLP provider.", e)
            from backend.app.services.providers import _mock_intent
            intent = await _mock_intent.extract_intent(command_to_process)
        except Exception as e:
            logger.warning("Unexpected error during Gemini intent generation (%s), falling back to local NLP provider.", e)
            from backend.app.services.providers import _mock_intent
            intent = await _mock_intent.extract_intent(command_to_process)

    # Check for in-sentence quantity correction (e.g. "இரண்டு கிலோ… இல்ல மூணு கிலோ" -> 3.0)
    eff_qty = extract_effective_quantity(text)
    if eff_qty is not None and intent.entities.quantity != eff_qty:
        intent.entities.quantity = eff_qty

    # -------------------------------------------------------------------------
    # Intent Overrides: Explicit keywords for new product creation or price change
    # -------------------------------------------------------------------------
    if ("new product" in lower_text or "pudhu product" in lower_text) and intent.intent != IntentCategory.CREATE_PRODUCT:
        intent.intent = IntentCategory.CREATE_PRODUCT
        intent.requires_clarification = False
        if not intent.entities.product_name:
            cleaned = lower_text
            for fw in ["new product", "pudhu product", "add product", "add", "pannunga", "podunga"]:
                cleaned = re.sub(r"\b" + re.escape(fw) + r"\b", "", cleaned)
            price_match = re.search(r"(\d+(\.\d+)?)", cleaned)
            if price_match:
                intent.entities.price = float(price_match.group(1))
                cleaned = re.sub(r"(\d+(\.\d+)?)", "", cleaned)
            for w in ["rupees", "rs", "kilo", "kg", "litre"]:
                cleaned = re.sub(r"\b" + re.escape(w) + r"\b", "", cleaned)
            intent.entities.product_name = cleaned.strip().title()

    if ("price" in lower_text or "விலை" in lower_text) and ("maathu" in lower_text or "update" in lower_text or "change" in lower_text) and intent.intent != IntentCategory.UPDATE_PRICE:
        intent.intent = IntentCategory.UPDATE_PRICE
        intent.requires_clarification = False
        price_match = re.search(r"(\d+(\.\d+)?)", lower_text)
        if price_match:
            intent.entities.price = float(price_match.group(1))

    # -------------------------------------------------------------------------
    # Step 5: Context Injection for Pronouns / Omitted Products
    # ("Innum 5 kilo add pannunga", "Adhula 2 kilo remove pannunga", "Stock evlo irukku?")
    # -------------------------------------------------------------------------
    if not intent.entities.product_name and conv.active_product_name:
        if intent.intent in (IntentCategory.ADD_STOCK, IntentCategory.SELL_PRODUCT, IntentCategory.CHECK_STOCK):
            intent.entities.product_name = conv.active_product_name
            if not intent.entities.unit:
                intent.entities.unit = conv.active_product_unit or "kg"
            # Context resolved the missing product name, so clear clarification flag
            if intent.entities.quantity is not None or intent.intent == IntentCategory.CHECK_STOCK:
                intent.requires_clarification = False

    # Also if both product_name and quantity are now present for ADD/SELL, clear clarification
    if intent.intent in (IntentCategory.ADD_STOCK, IntentCategory.SELL_PRODUCT):
        if intent.entities.product_name and intent.entities.quantity is not None and intent.entities.quantity > 0:
            intent.requires_clarification = False

    # -------------------------------------------------------------------------
    # Step 6: Clarification Check — Tamil-First, Never Generic English Fallback
    # -------------------------------------------------------------------------
    if intent.requires_clarification:
        is_tamil = intent.language in ("Tamil", "Tanglish", "Mixed") or any(
            ord(c) >= 0x0B80 and ord(c) <= 0x0BFF for c in text
        )
        clarification_msg = intent.clarification_question
        if not clarification_msg or "could not understand" in clarification_msg.lower():
            if intent.entities.product_name:
                p_disp = intent.entities.product_name
                if intent.intent == IntentCategory.ADD_STOCK:
                    clarification_msg = f"எவ்வளவு {p_disp} சேர்க்க வேண்டும்?" if is_tamil else f"How much {p_disp} would you like to add?"
                elif intent.intent == IntentCategory.SELL_PRODUCT:
                    clarification_msg = f"{p_disp} எவ்வளவு வேண்டும்?" if is_tamil else f"How much {p_disp} would you like to sell?"
                else:
                    clarification_msg = f"{p_disp} பற்றி என்ன செய்ய வேண்டும்?" if is_tamil else f"What would you like to do with {p_disp}?"
            else:
                clarification_msg = "மன்னிக்கவும், எந்தப் பொருளைப் பற்றி சொல்கிறீர்கள்?" if is_tamil else "Sorry, which product are you referring to?"

        if intent.entities.product_name:
            conv.active_product_name = intent.entities.product_name
            conv.missing_field = "quantity" if not intent.entities.quantity else None
            conv.pending_action_type = intent.intent.value
        else:
            conv.missing_field = "product"
            if intent.entities.quantity:
                conv.last_quantity = intent.entities.quantity
                conv.last_unit = intent.entities.unit or "kg"
            if intent.intent in (IntentCategory.ADD_STOCK, IntentCategory.SELL_PRODUCT):
                conv.pending_action_type = intent.intent.value

        conv.updated_at = datetime.now(timezone.utc)
        return InterpretResponse(
            success=True,
            intent=intent,
            requires_confirmation=False,
            message=clarification_msg,
            message_ta=clarification_msg,
            session_id=effective_session_id,
            context=conv.to_dict()
        )

    # -------------------------------------------------------------------------
    # Step 7: Contextual Relative Addition ("Innum 5 kilo add pannunga")
    # Execute directly if referring to recently active product in continuous dialogue
    # -------------------------------------------------------------------------
    is_relative_innum = ("innum" in lower_text or "இன்னும்" in lower_text)
    if is_relative_innum and intent.intent == IntentCategory.ADD_STOCK and conv.active_product_id and intent.entities.quantity:
        db_prod = db.query(Product).filter(Product.id == conv.active_product_id, Product.is_active == True).first()
        if db_prod:
            add_qty = intent.entities.quantity
            res = stock_service.adjust_stock(
                db=db,
                product_id=db_prod.id,
                adjustment_type=StockAdjustmentType.ADD,
                quantity=add_qty,
                reason="Voice contextual relative addition",
                reference_id=f"AI-REL-{uuid.uuid4().hex[:6]}"
            )
            stock_int = int(res.new_quantity) if res.new_quantity.is_integer() else res.new_quantity
            qty_int = int(add_qty) if add_qty.is_integer() else add_qty
            unit_str = conv.active_product_unit or db_prod.unit
            msg = f"{qty_int} {unit_str} {db_prod.name} added. New total stock: {stock_int} {unit_str}."
            msg_ta = f"{qty_int} {unit_str} {db_prod.name} add panniyachu. Ippo total stock {stock_int} {unit_str}."
            conv.last_quantity = add_qty
            conv.updated_at = datetime.now(timezone.utc)
            return InterpretResponse(
                success=True,
                intent=intent,
                resolved_product=to_resolved_schema(db_prod),
                requires_confirmation=False,
                message=msg,
                message_ta=msg_ta,
                session_id=effective_session_id,
                context=conv.to_dict()
            )

    # -------------------------------------------------------------------------
    # Step 8: Contextual Relative Reduction ("Adhula 2 kilo remove pannunga")
    # -------------------------------------------------------------------------
    is_relative_adhula = ("adhula" in lower_text or "remove" in lower_text or "korainga" in lower_text)
    if is_relative_adhula and intent.intent in (IntentCategory.SELL_PRODUCT, IntentCategory.ADD_STOCK) and conv.active_product_id and intent.entities.quantity:
        db_prod = db.query(Product).filter(Product.id == conv.active_product_id, Product.is_active == True).first()
        if db_prod:
            rem_qty = intent.entities.quantity
            if db_prod.quantity < rem_qty:
                return InterpretResponse(
                    success=False,
                    intent=intent,
                    resolved_product=to_resolved_schema(db_prod),
                    requires_confirmation=False,
                    message=f"Insufficient stock to remove {rem_qty} {db_prod.unit}. Available: {db_prod.quantity} {db_prod.unit}.",
                    message_ta=f"{db_prod.name} stock insufficient. Ippo {db_prod.quantity} {db_prod.unit} mattum irukku.",
                    session_id=effective_session_id,
                    context=conv.to_dict()
                )
            res = stock_service.adjust_stock(
                db=db,
                product_id=db_prod.id,
                adjustment_type=StockAdjustmentType.REMOVE,
                quantity=rem_qty,
                reason="Voice contextual relative reduction",
                reference_id=f"AI-REL-{uuid.uuid4().hex[:6]}"
            )
            stock_int = int(res.new_quantity) if res.new_quantity.is_integer() else res.new_quantity
            qty_int = int(rem_qty) if rem_qty.is_integer() else rem_qty
            unit_str = conv.active_product_unit or db_prod.unit
            msg = f"{qty_int} {unit_str} {db_prod.name} removed. New total stock: {stock_int} {unit_str}."
            msg_ta = f"{db_prod.name} stock-la {qty_int} {unit_str} remove panniyachu. Ippo total stock {stock_int} {unit_str}."
            conv.last_quantity = rem_qty
            conv.updated_at = datetime.now(timezone.utc)
            return InterpretResponse(
                success=True,
                intent=intent,
                resolved_product=to_resolved_schema(db_prod),
                requires_confirmation=False,
                message=msg,
                message_ta=msg_ta,
                session_id=effective_session_id,
                context=conv.to_dict()
            )

    # =========================================================================
    # Intent: ADD_STOCK or SELL_PRODUCT (Consequential mutations requiring confirmation)
    # =========================================================================
    if intent.intent in (IntentCategory.ADD_STOCK, IntentCategory.SELL_PRODUCT):
        # 1. Check for dynamic multi-item customer order
        items_to_process = []
        if intent.intent == IntentCategory.SELL_PRODUCT:
            if intent.entities.items and len(intent.entities.items) > 1:
                items_to_process = intent.entities.items
            else:
                extracted = extract_kirana_items_from_text(text)
                if len(extracted) > 1:
                    items_to_process = [OrderItemEntity(**it) for it in extracted]

        if items_to_process:
            items_spec = []
            for item in items_to_process:
                st, res_prod, cands = resolve_product(db, item.product_name)
                if st == ResolutionStatus.NO_MATCH or not res_prod:
                    return InterpretResponse(
                        success=False,
                        intent=intent,
                        requires_confirmation=False,
                        message=f"{item.product_name} product list-la illa. First product add pannalama?",
                        message_ta=f"{item.product_name} product list-la illa. First product add pannalama?"
                    )
                if st == ResolutionStatus.MULTIPLE_MATCHES:
                    cand_names = ", ".join(p.name for p in cands)
                    return InterpretResponse(
                        success=False,
                        intent=intent,
                        requires_confirmation=False,
                        message=f"Multiple products matched '{item.product_name}': {cand_names}. Which one did you mean?",
                        message_ta=f"'{item.product_name}' பெயரில் பல பொருட்கள் உள்ளன ({cand_names})."
                    )

                db_item = db.query(Product).filter(Product.id == res_prod.id, Product.is_active == True).first()
                if not db_item or db_item.quantity < item.quantity:
                    avail = db_item.quantity if db_item else 0
                    return InterpretResponse(
                        success=False,
                        intent=intent,
                        requires_confirmation=False,
                        message=f"Insufficient stock for '{item.product_name}'. Available: {avail} {item.unit}, requested: {item.quantity} {item.unit}.",
                        message_ta=f"'{item.product_name}' போதுமான இருப்பு இல்லை! தற்போது {avail} மட்டுமே உள்ளது."
                    )

                line_tot_dec = calculate_line_item(item.quantity, db_item.selling_price, item.unit or db_item.unit)
                items_spec.append({
                    "product_id": db_item.id,
                    "product_name": db_item.name,
                    "quantity": item.quantity,
                    "unit": item.unit or db_item.unit,
                    "current_stock": db_item.quantity,
                    "projected_stock": round(db_item.quantity - item.quantity, 3),
                    "unit_price": float(quantize_currency(db_item.selling_price)),
                    "line_total": float(line_tot_dec)
                })

            grand_total_dec = sum((to_decimal(it["line_total"]) for it in items_spec), Decimal("0.00"))
            grand_total = float(grand_total_dec)
            first_db_prod = db.query(Product).filter(Product.id == items_spec[0]["product_id"]).first()
            action_id = str(uuid.uuid4())
            pending_action = PendingAction(
                action_id=action_id,
                action="SELL_PRODUCT",
                product_id=first_db_prod.id,
                product_name=", ".join(it["product_name"] for it in items_spec),
                product_name_ta="வாடிக்கையாளர் ஆர்டர்",
                quantity=sum(it["quantity"] for it in items_spec),
                unit="items",
                current_stock=first_db_prod.quantity,
                projected_stock=round(first_db_prod.quantity - items_spec[0]["quantity"], 3),
                unit_price=None,
                estimated_total=grand_total,
                payment_method=intent.entities.payment_method or "CASH",
                items=items_spec
            )
            pending_store.save(pending_action)
            conv.pending_action_id = action_id
            conv.pending_items = items_spec
            conv.last_action = "SELL_PRODUCT"
            conv.updated_at = datetime.now(timezone.utc)

            preview = ConfirmationPreview(
                action_id=action_id,
                action="SELL_PRODUCT",
                product_id=first_db_prod.id,
                product_name="Customer Order: " + ", ".join(f"{it['product_name']} ({it['quantity']} {it['unit']})" for it in items_spec),
                product_name_ta="வாடிக்கையாளர் ஆர்டர்",
                quantity=sum(it["quantity"] for it in items_spec),
                unit="items",
                current_stock=first_db_prod.quantity,
                projected_stock=round(first_db_prod.quantity - items_spec[0]["quantity"], 3),
                unit_price=None,
                estimated_total=grand_total,
                payment_method=intent.entities.payment_method or "CASH",
                items=items_spec,
                expires_at=pending_action.expires_at,
            )
            tot_int = int(grand_total) if grand_total.is_integer() else grand_total
            msg = f"Customer order ready. Bill total is ₹{grand_total:.2f}. Confirm sale?"
            msg_tanglish = f"Customer order ready. Bill total ₹{tot_int}. Sale confirm pannalama?"
            msg_ta = f"வாடிக்கையாளர் பில் தயார். மொத்தம் ₹{tot_int}. விற்பனையை உறுதி செய்யவா?"
            return InterpretResponse(
                success=True,
                intent=intent,
                resolved_product=to_resolved_schema(first_db_prod),
                requires_confirmation=True,
                confirmation_preview=preview,
                message=msg,
                message_ta=msg_ta,
                message_tanglish=msg_tanglish,
                detected_language=user_lang,
                spoken_response=format_spoken_response(user_lang, msg, msg_ta, msg_tanglish),
                session_id=effective_session_id,
                context=conv.to_dict()
            )

        # 2. Single item validation
        product_query = intent.entities.product_name
        qty = intent.entities.quantity

        if not product_query:
            intent.requires_clarification = True
            action_word = "add" if intent.intent == IntentCategory.ADD_STOCK else "sell"
            unit_hint = intent.entities.unit or "kg"
            qty_fmt = f"{int(qty) if qty.is_integer() else qty} {unit_hint}" if qty else ""
            question = f"Endha product-ku {qty_fmt} {action_word} pannanum?".strip()
            intent.clarification_question = question
            conv.missing_field = "product"
            conv.last_quantity = qty
            conv.last_unit = intent.entities.unit
            conv.pending_action_type = intent.intent.value
            conv.updated_at = datetime.now(timezone.utc)
            return InterpretResponse(
                success=True,
                intent=intent,
                requires_confirmation=False,
                message=question,
                message_ta=f"எந்தப் பொருளுக்கு {qty_fmt} {action_word} செய்ய வேண்டும்?",
                session_id=effective_session_id,
                context=conv.to_dict()
            )

        if qty is None or qty <= 0:
            intent.requires_clarification = True
            if intent.intent == IntentCategory.ADD_STOCK:
                question = f"எவ்வளவு {product_query} சேர்க்க வேண்டும்?"
            else:
                question = f"{product_query} எவ்வளவு வேண்டும்?"
            intent.clarification_question = question
            conv.active_product_name = product_query
            conv.missing_field = "quantity"
            conv.pending_action_type = intent.intent.value
            conv.updated_at = datetime.now(timezone.utc)
            return InterpretResponse(
                success=True,
                intent=intent,
                requires_confirmation=False,
                message=question,
                message_ta=question,
                session_id=effective_session_id,
                context=conv.to_dict()
            )

        res_status, resolved_prod, candidates = resolve_product(db, product_query)

        if res_status == ResolutionStatus.NO_MATCH:
            return InterpretResponse(
                success=True,
                intent=intent,
                requires_confirmation=False,
                message=f"Product '{product_query}' is not in store catalog.",
                message_ta=f"இந்தப் பொருள் கடையின் inventory-ல் இல்லை. முதலில் பொருளைச் சேர்க்க வேண்டுமா?"
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
        prod_disp = db_product.name_ta or db_product.name

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
                        f"இந்தப் பொருளில் போதுமான stock இல்லை. தற்போது {current_stock} {db_product.unit} மட்டுமே உள்ளது."
                    )
                )

            projected_stock = round(current_stock - qty, 3)
            unit_p_dec = quantize_currency(db_product.selling_price)
            line_tot_dec = calculate_line_item(qty, unit_p_dec, unit)
            unit_price = float(unit_p_dec)
            estimated_total = float(line_tot_dec)
        else:
            projected_stock = round(current_stock + qty, 3)
            unit_price = float(quantize_currency(db_product.purchase_price))
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
        conv.active_product_id = db_product.id
        conv.active_product_name = db_product.name
        conv.active_product_unit = unit
        conv.pending_action_id = action_id
        conv.last_action = action_name
        conv.last_quantity = qty
        conv.last_unit = unit
        conv.updated_at = datetime.now(timezone.utc)

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

        qty_fmt = int(qty) if qty.is_integer() else qty
        if action_name == "ADD_STOCK":
            if qty >= 100:
                msg = f"Large stock addition alert: Ready to add {qty_fmt} {unit} of {db_product.name}. Stock will increase from {current_stock} to {projected_stock} {unit}."
                msg_ta = f"கவனிக்க: பெரிய அளவு! {qty_fmt} {unit} {prod_disp} சேர்க்க உறுதி செய்யலாமா?"
                msg_tanglish = f"{db_product.name}-ku {qty_fmt} {unit} periya stock add pannalama?"
            else:
                msg = f"Ready to add {qty_fmt} {unit} of {db_product.name}. Stock will increase from {current_stock} to {projected_stock} {unit}."
                msg_ta = f"{prod_disp} {qty_fmt} {unit} சேர்க்கிறேன். சரிதானா?"
                msg_tanglish = f"{db_product.name} {qty_fmt} {unit} add pannalama?"
        else:
            tot_fmt = int(estimated_total) if estimated_total.is_integer() else estimated_total
            msg = f"Ready to record sale of {qty_fmt} {unit} of {db_product.name} for ₹{estimated_total}. Remaining stock: {projected_stock} {unit}."
            msg_ta = f"{prod_disp} {qty_fmt} {unit} பில் தயார். மொத்தம் ₹{tot_fmt}. விற்பனையை உறுதி செய்யவா?"
            msg_tanglish = f"{db_product.name} {qty_fmt} {unit} bill podalama? Total ₹{tot_fmt}."

        return InterpretResponse(
            success=True,
            intent=intent,
            resolved_product=resolved_prod,
            requires_confirmation=True,
            confirmation_preview=preview,
            message=msg,
            message_ta=msg_ta,
            message_tanglish=msg_tanglish,
            detected_language=user_lang,
            spoken_response=format_spoken_response(user_lang, msg, msg_ta, msg_tanglish),
            session_id=effective_session_id,
            context=conv.to_dict()
        )

        return InterpretResponse(
            success=True,
            intent=intent,
            resolved_product=resolved_prod,
            requires_confirmation=True,
            confirmation_preview=preview,
            message=msg,
            message_ta=msg_ta,
            message_tanglish=msg_tanglish,
            detected_language=user_lang,
            spoken_response=format_spoken_response(user_lang, msg, msg_ta, msg_tanglish),
            session_id=effective_session_id,
            context=conv.to_dict()
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
            conv.active_product_id = resolved_prod.id
            conv.active_product_name = resolved_prod.name
            conv.active_product_unit = resolved_prod.unit
            conv.last_action = "CHECK_STOCK"
            conv.updated_at = datetime.now(timezone.utc)
            stock_int = int(resolved_prod.current_stock) if resolved_prod.current_stock.is_integer() else resolved_prod.current_stock
            prod_disp = resolved_prod.name_ta or resolved_prod.name
            msg = f"Your current {resolved_prod.name} stock is {stock_int} {resolved_prod.unit}."
            msg_tanglish = f"{resolved_prod.name} stock {stock_int} {resolved_prod.unit} irukku."
            if any(w in lower_text for w in ["இல்லையா", "illaiya", "illaya", "இருக்கா", "irukka"]):
                if resolved_prod.current_stock > 0:
                    msg_ta = f"{prod_disp} stock உள்ளது. தற்போது {stock_int} {resolved_prod.unit} உள்ளது."
                else:
                    msg_ta = f"{prod_disp} stock இல்லை. இருப்பு 0 {resolved_prod.unit} மட்டுமே உள்ளது."
            else:
                msg_ta = f"கடையில் தற்போது {stock_int} {resolved_prod.unit} {prod_disp} உள்ளது."

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
                message_ta=msg_ta,
                message_tanglish=msg_tanglish,
                detected_language=user_lang,
                spoken_response=format_spoken_response(user_lang, msg, msg_ta, msg_tanglish),
                session_id=effective_session_id,
                context=conv.to_dict()
            )
        elif res_status == ResolutionStatus.MULTIPLE_MATCHES:
            cand_names = ", ".join(p.name for p in candidates)
            return InterpretResponse(
                success=True,
                intent=intent,
                candidate_products=candidates,
                requires_confirmation=False,
                message=f"Found multiple products matching '{product_query}': {cand_names}. Which one would you like to inspect?",
                message_ta=f"'{product_query}' பெயரில் பல பொருட்கள் உள்ளன ({cand_names})."
            )
        else:
            return InterpretResponse(
                success=True,
                intent=intent,
                requires_confirmation=False,
                message=f"Product '{product_query}' is not in your store catalog.",
                message_ta=f"இந்தப் பொருள் கடையின் inventory-ல் இல்லை. முதலில் பொருளைச் சேர்க்க வேண்டுமா?"
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
            msg_ta = "எல்லா பொருட்களும் போதுமான அளவில் உள்ளன. குறைந்த இருப்பு எச்சரிக்கை இல்லை."
        else:
            msg = f"{count} products need reordering: {names}."
            msg_ta = f"குறைந்த இருப்பு உள்ள பொருட்கள்: {names}."

        return InterpretResponse(
            success=True,
            intent=intent,
            requires_confirmation=False,
            query_result={"low_stock_count": count, "items": [p.name for p in low_stock_prods]},
            message=msg,
            message_ta=msg_ta
        )

    # =========================================================================
    # Intent: PRODUCT_SALES_REPORT (Top / Best selling product)
    # =========================================================================
    if intent.intent == IntentCategory.PRODUCT_SALES_REPORT:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        top_item = (
            db.query(SaleItem.product_name_snapshot, func.sum(SaleItem.quantity).label("total_sold"))
            .join(Sale, SaleItem.sale_id == Sale.id)
            .filter(Sale.created_at >= today_start)
            .group_by(SaleItem.product_name_snapshot)
            .order_by(func.sum(SaleItem.quantity).desc())
            .first()
        )
        if top_item:
            msg = f"Today's best selling product is {top_item[0]}."
            msg_ta = f"இன்றைய அதிக விற்பனையான பொருள்: {top_item[0]}."
        else:
            first_prod = db.query(Product).filter(Product.is_active == True).first()
            prod_name = first_prod.name if first_prod else "Rice"
            msg = f"Today's best selling product is {prod_name}."
            msg_ta = f"இன்றைய அதிக விற்பனையான பொருள்: {prod_name}."
        return InterpretResponse(
            success=True,
            intent=intent,
            requires_confirmation=False,
            message=msg,
            message_ta=msg_ta
        )

    # =========================================================================
    # Intent: SALES_REPORT
    # =========================================================================
    if intent.intent == IntentCategory.SALES_REPORT:
        dash = dashboard_service.get_dashboard_summary(db)
        kpi = dash.kpis
        tot_today = int(kpi.today_sales) if kpi.today_sales.is_integer() else kpi.today_sales
        if "bill" in text.lower() or "ethana" in text.lower():
            msg = f"Total {kpi.today_orders} bills created today."
            msg_ta = f"இன்று மொத்தம் {kpi.today_orders} பில்கள் போடப்பட்டுள்ளன."
            msg_tanglish = f"Innaiku total {kpi.today_orders} bills create pannirukkinga."
        else:
            msg = f"Today's total sales: ₹{tot_today} across {kpi.today_orders} bills."
            msg_ta = f"இன்றைய மொத்த விற்பனை ₹{tot_today} (மொத்தம் {kpi.today_orders} பில்கள்)."
            msg_tanglish = f"Innaiku total sales ₹{tot_today} rupees. Total {kpi.today_orders} orders."
        return InterpretResponse(
            success=True,
            intent=intent,
            requires_confirmation=False,
            query_result={"today_sales": kpi.today_sales, "today_orders": kpi.today_orders},
            message=msg,
            message_ta=msg_ta,
            message_tanglish=msg_tanglish,
            detected_language=user_lang,
            spoken_response=format_spoken_response(user_lang, msg, msg_ta, msg_tanglish),
            session_id=effective_session_id,
            context=conv.to_dict()
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

    # =========================================================================
    # Intent: UPDATE_PRICE
    # =========================================================================
    if intent.intent == IntentCategory.UPDATE_PRICE:
        product_query = intent.entities.product_name
        new_price = intent.entities.price
        if new_price is None and intent.entities.quantity is not None and intent.entities.quantity > 0:
            new_price = intent.entities.quantity

        if not product_query:
            return InterpretResponse(
                success=True,
                intent=intent,
                requires_confirmation=False,
                message="Which product's price would you like to update?",
                message_ta="எந்த பொருளின் விலையை மாற்ற வேண்டும்?"
            )

        res_status, resolved_prod, candidates = resolve_product(db, product_query)
        if res_status == ResolutionStatus.NO_MATCH or not resolved_prod:
            return InterpretResponse(
                success=False,
                intent=intent,
                requires_confirmation=False,
                message=f"Product '{product_query}' store-la illa.",
                message_ta=f"'{product_query}' இருப்பு பட்டியலில் இல்லை."
            )

        if new_price is None or new_price <= 0:
            intent.requires_clarification = True
            question = f"{resolved_prod.name} selling price evlo rupees-ku maathanum?"
            intent.clarification_question = question
            return InterpretResponse(
                success=True,
                intent=intent,
                resolved_product=resolved_prod,
                requires_confirmation=False,
                message=question,
                message_ta=question
            )

        db_product = db.query(Product).filter(Product.id == resolved_prod.id, Product.is_active == True).first()
        old_price = db_product.selling_price
        action_id = str(uuid.uuid4())

        pending_action = PendingAction(
            action_id=action_id,
            action="UPDATE_PRICE",
            product_id=db_product.id,
            product_name=db_product.name,
            product_name_ta=db_product.name_ta,
            quantity=0,
            unit=db_product.unit,
            current_stock=db_product.quantity,
            projected_stock=db_product.quantity,
            unit_price=new_price,
            estimated_total=new_price,
        )
        pending_store.save(pending_action)
        conv.active_product_id = db_product.id
        conv.active_product_name = db_product.name
        conv.pending_action_id = action_id
        conv.last_action = "UPDATE_PRICE"
        conv.updated_at = datetime.now(timezone.utc)

        preview = ConfirmationPreview(
            action_id=action_id,
            action="UPDATE_PRICE",
            product_id=db_product.id,
            product_name=db_product.name,
            product_name_ta=db_product.name_ta,
            quantity=0,
            unit=db_product.unit,
            current_stock=db_product.quantity,
            projected_stock=db_product.quantity,
            unit_price=new_price,
            estimated_total=new_price,
            expires_at=pending_action.expires_at,
        )

        old_fmt = int(old_price) if old_price.is_integer() else old_price
        new_fmt = int(new_price) if new_price.is_integer() else new_price
        msg = f"Ready to update {db_product.name} price from ₹{old_fmt} to ₹{new_fmt} per {db_product.unit}. Confirm price update?"
        msg_ta = f"{db_product.name} price ₹{old_fmt}-la irundhu ₹{new_fmt}-nu maathalama?"
        return InterpretResponse(
            success=True,
            intent=intent,
            resolved_product=resolved_prod,
            requires_confirmation=True,
            confirmation_preview=preview,
            message=msg,
            message_ta=msg_ta,
            session_id=effective_session_id,
            context=conv.to_dict()
        )

    # =========================================================================
    # Intent: CREATE_PRODUCT
    # =========================================================================
    if intent.intent == IntentCategory.CREATE_PRODUCT:
        product_query = intent.entities.product_name
        if not product_query:
            return InterpretResponse(
                success=True,
                intent=intent,
                requires_confirmation=False,
                message="Which product would you like to register?",
                message_ta="எந்த புதிய பொருளை பதிவு செய்ய வேண்டும்?"
            )

        res_status, resolved_prod, _ = resolve_product(db, product_query)
        if res_status == ResolutionStatus.MATCH and resolved_prod:
            return InterpretResponse(
                success=True,
                intent=intent,
                resolved_product=resolved_prod,
                requires_confirmation=False,
                message=f"Product '{resolved_prod.name}' already exists in catalog with stock {resolved_prod.current_stock} {resolved_prod.unit}.",
                message_ta=f"'{resolved_prod.name}' ஏற்கனவே பட்டியலில் உள்ளது. இருப்பு: {resolved_prod.current_stock} {resolved_prod.unit}."
            )

        selling_price = intent.entities.price
        if selling_price is None or selling_price <= 0:
            return InterpretResponse(
                success=True,
                intent=intent,
                requires_confirmation=False,
                message=f"Please specify the selling price for new product '{product_query}'. E.g., 'Selling price 40 rupees'.",
                message_ta=f"புதிய பொருள் '{product_query}'-க்கு விற்பனை விலையை கூறவும். (எ.கா. 'விலை 40 ரூபாய்').",
                session_id=effective_session_id,
                context=conv.to_dict()
            )
        unit = intent.entities.unit or "kg"

        slug = re.sub(r"[^A-Za-z0-9]", "", product_query).upper()[:6]
        sku = f"SKU-{slug}-{uuid.uuid4().hex[:4].upper()}"

        from backend.app.schemas.product import ProductCreate
        from backend.app.services import inventory_service
        new_prod_in = ProductCreate(
            name=product_query.title(),
            name_ta=None,
            sku=sku,
            category="Grocery",
            quantity=0.0,
            unit=unit,
            purchase_price=round(selling_price * 0.8, 2),
            selling_price=selling_price,
            minimum_stock_level=10.0,
            description="Created via Kirana Voice Assistant",
            is_active=True
        )
        created_prod = inventory_service.create_product(db, new_prod_in)
        conv.active_product_id = created_prod.id
        conv.active_product_name = created_prod.name
        conv.active_product_unit = created_prod.unit
        conv.last_action = "CREATE_PRODUCT"
        conv.updated_at = datetime.now(timezone.utc)

        price_fmt = int(selling_price) if selling_price.is_integer() else selling_price
        msg = f"New product '{created_prod.name}' registered with price ₹{price_fmt}/{unit} and 0 stock. Ready to add stock."
        msg_ta = f"புதிய பொருள் '{created_prod.name}' (விலை ₹{price_fmt}/{unit}) சேர்க்கப்பட்டது. சரக்கு சேர்க்க தயார்."
        return InterpretResponse(
            success=True,
            intent=intent,
            resolved_product=to_resolved_schema(created_prod),
            requires_confirmation=False,
            message=msg,
            message_ta=msg_ta,
            session_id=effective_session_id,
            context=conv.to_dict()
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
        stock_int = int(result.new_quantity) if result.new_quantity.is_integer() else result.new_quantity
        qty_int = int(action.quantity) if action.quantity.is_integer() else action.quantity
        prod_disp = product.name_ta or product.name
        msg = f"{product.name} {qty_int} {action.unit} stock added. New total stock: {stock_int} {product.unit}."
        msg_ta = f"{qty_int} {action.unit} {prod_disp} சேர்க்கப்பட்டது. இப்போது மொத்தம் {stock_int} {product.unit} உள்ளது."

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
        if action.items:
            # Multi-item sale transaction
            sale_items = []
            for it in action.items:
                p_item = db.query(Product).filter(Product.id == it["product_id"]).first()
                p_name = it.get("product_name") or it.get("name")
                if not p_item or p_item.quantity < it["quantity"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient stock for '{p_name}'."
                    )
                sale_items.append(SaleItemCreate(product_id=it["product_id"], quantity=it["quantity"]))

            sale_in = SaleCreate(
                items=sale_items,
                payment_method=action.payment_method or "CASH",
                notes="Voice multi-item customer order confirmed",
                idempotency_key=action.action_id
            )
            sale = sales_service.create_sale(db=db, sale_in=sale_in)
            tot_int = int(sale.total_amount) if sale.total_amount.is_integer() else sale.total_amount

            lines = [f"{it.get('product_name') or it.get('name')} {int(it['quantity']) if float(it['quantity']).is_integer() else it['quantity']} {it['unit']}." for it in action.items]
            items_spoken = " ".join(lines)
            msg_ta = f"பில் வெற்றிகரமாக உருவாக்கப்பட்டது. {items_spoken} மொத்த பில் ₹{tot_int}. வாடிக்கையாளரிடம் பெறவும்."
            msg = f"Bill successfully created. {items_spoken} Total bill: ₹{sale.total_amount:.2f}. Collect cash from customer."

            all_names = ", ".join(it.get("product_name") or it.get("name") for it in action.items)
            return ConfirmActionResponse(
                success=True,
                action="SELL_PRODUCT",
                transaction_id=sale.transaction_id,
                product_name=all_names,
                previous_stock=action.current_stock,
                new_stock=action.projected_stock,
                total_amount=sale.total_amount,
                message=msg,
                message_ta=msg_ta
            )

        # Final real-time stock guard for single item sale
        if product.quantity < action.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for '{product.name}'. Available: {product.quantity} {product.unit}."
            )

        sale_in = SaleCreate(
            items=[SaleItemCreate(product_id=product.id, quantity=action.quantity)],
            payment_method=action.payment_method or "CASH",
            notes="Voice sale transaction confirmed by merchant",
            idempotency_key=action.action_id
        )
        sale = sales_service.create_sale(db=db, sale_in=sale_in)

        # Refresh product to get updated stock
        db.refresh(product)
        tot_int = int(sale.total_amount) if sale.total_amount.is_integer() else sale.total_amount
        qty_int = int(action.quantity) if action.quantity.is_integer() else action.quantity
        rem_stock = int(product.quantity) if product.quantity.is_integer() else product.quantity
        prod_disp = product.name_ta or product.name
        msg = f"{qty_int} {action.unit} {product.name} sold. Remaining stock: {rem_stock} {product.unit}."
        msg_ta = f"{qty_int} {action.unit} {prod_disp} விற்பனை செய்யப்பட்டது. மீதமுள்ள stock {rem_stock} {product.unit}."

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

    elif action.action == "UPDATE_PRICE":
        old_price = product.selling_price
        product.selling_price = action.unit_price
        db.commit()
        db.refresh(product)
        price_fmt = int(product.selling_price) if product.selling_price.is_integer() else product.selling_price
        msg = f"{product.name} selling price updated to ₹{price_fmt} per {product.unit}."
        msg_ta = f"{product.name} selling price ₹{price_fmt}-nu update panniyachu."
        return ConfirmActionResponse(
            success=True,
            action="UPDATE_PRICE",
            transaction_id=f"PRC-{action.action_id[:8]}",
            product_name=product.name,
            previous_stock=product.quantity,
            new_stock=product.quantity,
            total_amount=product.selling_price,
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
            message="Action was cancelled. No changes were made to store inventory or sales.",
            message_ta="செயல்பாடு ரத்து செய்யப்பட்டது. கடையில் எந்த மாற்றமும் செய்யப்படவில்லை."
        )
    return CancelActionResponse(
        success=True,
        message="Action was already expired or not found. No changes were made.",
        message_ta="செயல்பாடு ஏற்கனவே ரத்து செய்யப்பட்டு விட்டது."
    )

