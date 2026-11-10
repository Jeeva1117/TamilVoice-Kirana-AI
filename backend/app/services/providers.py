"""Provider Interfaces and Implementations for Antigravity Kirana AI.
Defines clean abstract interfaces and swappable Mock and Real providers:
- STTProvider: MockSTTProvider & GnaniPrismaSTTProvider
- IntentProvider: MockIntentProvider & GeminiIntentProvider
- TTSProvider: MockTTSProvider & GnaniTimbreTTSProvider

Adheres strictly to API Credit Protection (~5,000 Gnani credits remaining, 0 consumed in mock).
"""
import re
import io
import math
import wave
import struct
import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, Dict, Any

from backend.app.config import settings
from backend.app.schemas.voice import TranscribeResponse
from backend.app.schemas.ai import (
    CommandIntent,
    CommandEntities,
    OrderItemEntity,
    IntentCategory,
    normalize_unit_str,
)
from backend.app.services.speech_normalizer import (
    normalize_spoken_numbers,
    extract_kirana_items_from_text,
    detect_spoken_language,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 1. SPEECH-TO-TEXT (STT) PROVIDER INTERFACE
# =============================================================================

class STTProvider(ABC):
    """Abstract interface for Speech-to-Text transcription."""

    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "recording.wav",
        content_type: str = "audio/wav",
        language: str = "ta-IN",
    ) -> TranscribeResponse:
        pass


class MockSTTProvider(STTProvider):
    """Deterministic Mock STT Provider for virtual testing and demo runs."""

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "recording.wav",
        content_type: str = "audio/wav",
        language: str = "ta-IN",
    ) -> TranscribeResponse:
        size = len(audio_bytes) if audio_bytes else 0
        transcript = "Innaiku 5 kilo rice stock add pannunga."

        return TranscribeResponse(
            success=True,
            transcript=transcript,
            provider="mock_prisma",
            model="mock-prisma-v2.5",
            language=language,
            detected_language="ta-IN",
            confidence=0.96,
            is_mock=True,
            duration_seconds=round(max(1.0, size / 32000.0), 2),
            audio_size_bytes=size,
            message="Transcribed using Mock STT Provider (API key preserved).",
        )


class GnaniPrismaSTTProvider(STTProvider):
    """Live Gnani Prisma v2.5 STT REST Provider."""

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "recording.wav",
        content_type: str = "audio/wav",
        language: str = "ta-IN",
    ) -> TranscribeResponse:
        from backend.app.services.gnani_stt_service import gnani_stt_service
        return await gnani_stt_service.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
            language=language,
        )


# =============================================================================
# 2. INTENT UNDERSTANDING PROVIDER INTERFACE
# =============================================================================

class IntentProvider(ABC):
    """Abstract interface for Natural Language Intent & Entity Extraction."""

    @abstractmethod
    async def extract_intent(self, text: str) -> CommandIntent:
        pass


def _match_product_from_text(lower_text: str) -> Tuple[Optional[str], str, Optional[str]]:
    """Helper to resolve Kirana catalog product, default unit, and Tamil display name."""
    if "gold winner" in lower_text or "goldwinner" in lower_text:
        return "Gold Winner Oil", "litre", "சூரியகாந்தி எண்ணெய்"
    if re.search(r"\boil\b", lower_text) or "எண்ணெய்" in lower_text:
        return "Gold Winner Oil", "litre", "சூரியகாந்தி எண்ணெய்"
    if any(w in lower_text for w in ["wheat", "godhumai", "gothumai", "atta", "கோதுமை"]):
        return "Wheat Flour", "kg", "கோதுமை மாவு"
    if any(w in lower_text for w in ["tomato", "thakkali", "தக்காளி"]):
        return "Tomato", "kg", "தக்காளி"
    if any(w in lower_text for w in ["onion", "vengayam", "வெங்காயம்"]):
        return "Onion", "kg", "வெங்காயம்"
    if any(w in lower_text for w in ["tea powder", "டீ தூள்", "தேயிலை தூள்", "தேயிலை", "டீ"]):
        return "Tea Powder", "packet", "டீ தூள்"
    if any(w in lower_text for w in ["masala", "மசாலா"]):
        return "Masala Powder", "packet", "மசாலா"
    if any(w in lower_text for w in ["milk", "paal", "பால்"]):
        return "Milk", "litre", "பால்"
    if any(w in lower_text for w in ["sugar", "sarkarai", "sakkarai", "seeni", "சர்க்கரை", "சீனி"]):
        return "Sugar", "kg", "சர்க்கரை"
    if any(w in lower_text for w in ["rice", "arisi", "ponni", "அரிசி"]):
        return "Ponni Boiled Rice", "kg", "அரிசி"
    if any(w in lower_text for w in ["honey", "thean", "then", "தேன்"]):
        return "Pure Honey", "bottle", "தேன்"
    if any(w in lower_text for w in ["country ginger", "ginger", "inji", "injii", "இஞ்சி"]):
        return "Ginger", "kg", "இஞ்சி"
    if any(w in lower_text for w in ["country garlic", "garlic", "poondu", "பூண்டு"]):
        return "Country Garlic", "kg", "பூண்டு"
    if any(w in lower_text for w in ["potato", "urulaikilangu", "urulai", "உருளைக்கிழங்கு"]):
        return "Potato", "kg", "உருளைக்கிழங்கு"
    if any(w in lower_text for w in ["carrot", "கேரட்"]):
        return "Carrot", "kg", "கேரட்"
    if any(w in lower_text for w in ["green chilli", "pachai milagai", "பச்சை மிளகாய்"]):
        return "Green Chilli", "kg", "பச்சை மிளகாய்"
    if any(w in lower_text for w in ["apple", "ஆப்பிள்"]):
        return "Apple", "kg", "ஆப்பிள்"
    if any(w in lower_text for w in ["banana", "vazhaipazham", "வாழைப்பழம்"]):
        return "Banana", "dozen", "வாழைப்பழம்"
    if any(w in lower_text for w in ["tata salt", "salt", "uppu", "உப்பு"]):
        return "Tata Salt", "packet", "உப்பு"
    if any(w in lower_text for w in ["toor dal", "tuvaram", "துவரம்"]):
        return "Toor Dal", "kg", "துவரம் பருப்பு"
    if any(w in lower_text for w in ["urad dal", "ulundhu", "உளுந்து"]):
        return "Urad Dal", "kg", "உளுத்தம் பருப்பு"
    if any(w in lower_text for w in ["ghee", "nei", "நெய்"]):
        return "Ghee", "bottle", "நெய்"
    if any(w in lower_text for w in ["maida", "மைதா"]):
        return "Maida", "kg", "மைதா"
    if any(w in lower_text for w in ["rava", "sooji", "ரவை"]):
        return "Rava", "kg", "ரவை"
    if any(w in lower_text for w in ["milk bread", "bread", "பிரெட்"]):
        return "Milk Bread", "packet", "பிரெட்"
    if any(w in lower_text for w in ["marie gold", "biscuit", "biscuits", "பிஸ்கட்"]):
        return "Marie Gold Biscuits", "packet", "பிஸ்கட்"
    if any(w in lower_text for w in ["dairy milk", "chocolate", "chocolates", "சாக்லேட்"]):
        return "Dairy Milk Chocolate", "piece", "சாக்லேட்"
    if any(w in lower_text for w in ["potato chips", "chips", "snacks", "சிப்ஸ்"]):
        return "Potato Chips Snacks", "packet", "ஸ்நாக்ஸ்"
    if any(w in lower_text for w in ["clinic plus", "shampoo", "ஷாம்பு"]):
        return "Clinic Plus Shampoo", "bottle", "ஷாம்பு"
    if any(w in lower_text for w in ["hair serum", "serum", "சீரம்"]):
        return "Hair Serum", "bottle", "ஹேர் சீரம்"
    if any(w in lower_text for w in ["hamam", "soap", "சோப்பு"]):
        return "Hamam Soap", "piece", "சோப்பு"
    if any(w in lower_text for w in ["colgate", "toothpaste", "டூத்பேஸ்ட்"]):
        return "Colgate Toothpaste", "piece", "டூத்பேஸ்ட்"
    if any(w in lower_text for w in ["notebook", "classmate", "நோட்டு"]):
        return "Classmate Notebook", "piece", "நோட்டுப் புத்தகம்"
    if any(w in lower_text for w in ["reynolds", "ball pen", "pen", "paena", "பேனா"]):
        if "pencil" not in lower_text and "பென்சில்" not in lower_text:
            return "Reynolds Ball Pen", "piece", "பேனா"
    if any(w in lower_text for w in ["scale", "ruler", "ஸ்கேல்"]):
        return "Plastic Scale 30cm", "piece", "ஸ்கேல்"
    if any(w in lower_text for w in ["pencil", "apsara", "பென்சில்"]):
        return "Apsara Pencil Box", "packet", "பென்சில்"
    if any(w in lower_text for w in ["eraser", "rubber", "அழிப்பான்"]):
        return "Dust-Free Eraser", "piece", "அழிப்பான்"
    if any(w in lower_text for w in ["paper", "copier", "பேப்பர்"]):
        return "A4 Copier Paper", "packet", "பேப்பர்"
    if any(w in lower_text for w in ["battery", "batteries", "aa battery", "பேட்டரி"]):
        return "AA Battery", "piece", "பேட்டரி"
    if any(w in lower_text for w in ["surf excel", "detergent", "சோப்புத்தூள்"]):
        return "Surf Excel Detergent", "packet", "டிட்டர்ஜென்ட்"
    if any(w in lower_text for w in ["vim", "dishwash", "டிஷ்வாஷ்"]):
        return "Vim Dishwash Liquid", "bottle", "டிஷ்வாஷ்"
    return None, "kg", None


class MockIntentProvider(IntentProvider):
    """
    Intelligent Rule-Based Mock Gemini Provider.
    Accurately maps Kirana shopkeeper Tamil, Tanglish, and English commands
    into strictly structured CommandIntent objects.
    """

    async def extract_intent(self, text: str) -> CommandIntent:
        raw = text.strip()
        detected_lang = detect_spoken_language(raw)
        # Normalize Tamil & Tanglish number words to digits first
        norm_text = normalize_spoken_numbers(raw)
        lower = norm_text.lower()

        # -----------------------------------------------------------------
        # Pattern 0A: Affirmative Confirmation ("Aama", "Seri", "Confirm", "Confirm pannunga", "Pannidunga", "Yes")
        # -----------------------------------------------------------------
        affirmative_words = [
            "aama", "aam", "seri", "confirm", "confirm pannunga", "pannidunga", "kodu",
            "yes", "seringa", "kudunga", "pannunga", "aama pannunga", "seri pannunga",
            "ஆமா", "ஆம்", "சரி", "உறுதி", "உறுதிப்படுத்து"
        ]
        is_affirmative = (
            lower in affirmative_words or
            re.match(r"^(?:aama|seri|confirm|yes|kodu|ஆமா|சரி|ஆம்)(?:\s+(?:pannunga|pannidunga|pannalam|kudunga))?[.!]?$", lower) is not None
        )
        if is_affirmative:
            return CommandIntent(
                intent=IntentCategory.CONFIRM_ACTION,
                language=detected_lang,
                original_text=raw,
                normalized_text="Confirm pending operation",
                entities=CommandEntities(),
                confidence=0.99,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 0B: Cancellation ("Cancel", "Cancel pannunga", "Vendaam", "Venaam", "Vendam", "No")
        # -----------------------------------------------------------------
        cancellation_words = [
            "cancel", "cancel pannunga", "vendaam", "venaam", "vendam", "vendang",
            "no", "nirutha", "வேண்டாம்", "ரத்து", "ரத்து செய்"
        ]
        is_cancellation = (
            lower in cancellation_words or
            re.match(r"^(?:cancel|vendaam|venaam|vendam|no|ரத்து)(?:\s+(?:pannunga|pannidunga|seiyavum))?[.!]?$", lower) is not None
        )
        if is_cancellation:
            return CommandIntent(
                intent=IntentCategory.CANCEL_ACTION,
                language=detected_lang,
                original_text=raw,
                normalized_text="Cancel pending operation",
                entities=CommandEntities(),
                confidence=0.99,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 0B.1: Politeness & Gratitude ("Thank you", "நன்றி", "Thanks", "Nandri")
        # -----------------------------------------------------------------
        thank_words = ["thank you", "thanks", "நன்றி", "nandri", "thank you so much", "okay thank you", "romba nandri", "thx"]
        is_thank_you = lower in thank_words or bool(re.search(r"\b(?:thank you|thanks|நன்றி|nandri)\b", lower))
        if is_thank_you:
            return CommandIntent(
                intent=IntentCategory.THANK_YOU,
                language=detected_lang,
                original_text=raw,
                normalized_text="Merchant expressed gratitude",
                entities=CommandEntities(),
                confidence=0.99,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 0B.2: Greetings ("Vanakkam", "வணக்கம்", "Hello", "Hi")
        # -----------------------------------------------------------------
        greeting_words = ["vanakkam", "vanakam", "வணக்கம்", "hello", "hi", "namaste", "good morning", "good evening"]
        is_greeting = lower in greeting_words or any(re.match(rf"^(?:{gw})(?:\s+(?:assistant|ai|sir|ji|pa))?[.!]*$", lower) for gw in greeting_words)
        if is_greeting:
            return CommandIntent(
                intent=IntentCategory.GREETING,
                language=detected_lang,
                original_text=raw,
                normalized_text="Merchant greeting",
                entities=CommandEntities(),
                confidence=0.99,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 0C: Contextual Relative Addition ("Innum 5 kilo add pannunga", "innum 5 add pannu")
        # -----------------------------------------------------------------
        if ("innum" in lower or "இன்னும்" in lower) and not ("sales" in lower or "report" in lower):
            qty_match = re.search(r"(\d+(\.\d+)?)", lower)
            qty = float(qty_match.group(1)) if qty_match else 5.0
            unit = "kg"
            if "litre" in lower or "லிட்டர்" in lower:
                unit = "litre"
            elif "packet" in lower or "பாக்கெட்" in lower:
                unit = "packet"
            return CommandIntent(
                intent=IntentCategory.ADD_STOCK,
                language="Tanglish",
                original_text=raw,
                normalized_text=f"Add {qty} {unit} more to current product in context",
                entities=CommandEntities(product_name=None, quantity=qty, unit=unit),
                confidence=0.98,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 0D: Contextual Relative Reduction ("Adhula 2 kilo remove pannunga", "Adhula 2 kilo kammi pannunga")
        # Only matches explicit pronoun references ("adhula", "athula", "adula", "அதுல", "அதில்")
        # -----------------------------------------------------------------
        if any(w in lower for w in ["adhula", "athula", "adula", "அதுல", "அதில்", "adhil"]) and not ("low stock" in lower or "stock evlo" in lower):
            qty_match = re.search(r"(\d+(\.\d+)?)", lower)
            qty = float(qty_match.group(1)) if qty_match else 2.0
            unit = "kg"
            if "litre" in lower or "லிட்டர்" in lower:
                unit = "litre"
            elif "packet" in lower or "பாக்கெட்" in lower:
                unit = "packet"
            return CommandIntent(
                intent=IntentCategory.SELL_PRODUCT,
                language="Tanglish",
                original_text=raw,
                normalized_text=f"Reduce {qty} {unit} from current product in context",
                entities=CommandEntities(product_name=None, quantity=qty, unit=unit),
                confidence=0.98,
                requires_clarification=False,
            )

        is_tamil_script = bool(re.search(r"[\u0B80-\u0BFF]", raw))

        # -----------------------------------------------------------------
        # Pattern 1: Multi-Item Sale
        # "Customer-ku one kilo tomato, two kilo onion, three kilo rice, two litre milk, two packet sugar, two packet tea powder sale pannunga"
        # -----------------------------------------------------------------
        multi_items = extract_kirana_items_from_text(raw)
        if len(multi_items) >= 2 and ("sale" in lower or "sell" in lower or "note" in lower or "kuduthuten" in lower or "customer" in lower or "bill" in lower or "பில்" in lower):
            items_entities = [OrderItemEntity(**it) for it in multi_items]
            total_qty = sum(it.quantity for it in items_entities)
            item_names_str = ", ".join(f"{it.quantity} {it.unit} {it.product_name}" for it in items_entities)
            return CommandIntent(
                intent=IntentCategory.SELL_PRODUCT,
                language="Tamil" if is_tamil_script else "Tanglish",
                original_text=raw,
                normalized_text=f"Record multi-item customer sale: {item_names_str}",
                entities=CommandEntities(
                    product_name="Multiple Items",
                    quantity=total_qty,
                    unit="items",
                    customer_name="Customer",
                    payment_method="CASH",
                    items=items_entities
                ),
                confidence=0.98,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 1B: CREATE_PRODUCT (Voice registration of new shop items)
        # -----------------------------------------------------------------
        if any(kw in lower for kw in ["new product", "pudhu product", "add product", "புது பொருள்", "register product"]):
            cleaned = lower
            for fw in ["new product", "pudhu product", "add product", "register product", "add", "pannunga", "podunga", "please", "price", "விலை", "rate", "cost"]:
                cleaned = re.sub(r"\b" + re.escape(fw) + r"\b", "", cleaned)
            price_match = re.search(r"(\d+(\.\d+)?)", lower)
            price_val = float(price_match.group(1)) if price_match else 50.0
            cleaned = re.sub(r"(\d+(\.\d+)?)", "", cleaned)
            for w in ["rupees", "rs", "kilo", "kg", "litre", "per", "piece", "packet", "பாக்கெட்", "ரூபாய்"]:
                cleaned = re.sub(r"\b" + re.escape(w) + r"\b", "", cleaned)
            prod_name = cleaned.strip().title() or "New Item"

            unit = "piece" if any(w in lower for w in ["toothpaste", "brush", "soap", "pen", "notebook"]) else ("litre" if "litre" in lower else "kg")

            return CommandIntent(
                intent=IntentCategory.CREATE_PRODUCT,
                language="Tamil" if is_tamil_script else "Tanglish",
                original_text=raw,
                normalized_text=f"Register new product {prod_name} at ₹{price_val}/{unit}",
                entities=CommandEntities(product_name=prod_name, price=price_val, quantity=price_val, unit=unit),
                confidence=0.98,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 1C: UPDATE_PRICE (Voice selling price adjustment)
        # -----------------------------------------------------------------
        if ("price" in lower or "rate" in lower or "vilai" in lower or "விலை" in lower) and any(w in lower for w in ["maathu", "mathu", "update", "change", "set pannu", "maathunga"]) and not any(kw in lower for kw in ["check", "evlo", "எவ்வளவு", "new product", "pudhu product", "add product", "register product", "புது பொருள்"]):
            prod, def_unit, prod_ta = _match_product_from_text(lower)
            prod = prod or "Ponni Boiled Rice"
            price_match = re.search(r"(\d+(\.\d+)?)", lower)
            price_val = float(price_match.group(1)) if price_match else None

            return CommandIntent(
                intent=IntentCategory.UPDATE_PRICE,
                language="Tamil" if is_tamil_script else "Tanglish",
                original_text=raw,
                normalized_text=f"Update selling price for {prod} to ₹{price_val}",
                entities=CommandEntities(product_name=prod, price=price_val, quantity=price_val),
                confidence=0.97,
                requires_clarification=False if price_val else True,
                clarification_question=None if price_val else (f"{prod_ta or prod} விலை எவ்வளவு ரூபாய்?" if is_tamil_script else f"{prod} selling price evlo rupees?"),
            )

        # -----------------------------------------------------------------
        # Pattern 2: Missing Product (e.g. "5 kilo add pannunga", "add 5 kg")
        # -----------------------------------------------------------------
        prod, def_unit, prod_ta = _match_product_from_text(lower)
        unit = def_unit
        if "litre" in lower or "லிட்டர்" in lower:
            unit = "litre"
        elif "packet" in lower or "பாக்கெட்" in lower:
            unit = "packet"
        elif "kilo" in lower or "kg" in lower or "கிலோ" in lower:
            unit = "kg"

        if not prod and ("add" in lower or "சேர்க்க" in lower or ("stock" in lower and not ("low" in lower or "kammi" in lower or "evlo" in lower or "report" in lower or "check" in lower or "sollu" in lower))):
            qty_match = re.search(r"(\d+(\.\d+)?)", lower)
            qty = float(qty_match.group(1)) if qty_match else None
            return CommandIntent(
                intent=IntentCategory.ADD_STOCK,
                language="Tamil" if is_tamil_script else "Tanglish",
                original_text=raw,
                normalized_text="Add stock (product unspecified)",
                entities=CommandEntities(product_name=None, quantity=qty, unit=unit),
                confidence=0.92,
                requires_clarification=True,
                clarification_question="எந்தப் பொருளைப் பற்றி சொல்கிறீர்கள்?" if is_tamil_script else "Endha product add pannanum?",
            )

        # -----------------------------------------------------------------
        # Pattern 3: Bill Creation ("மசாலா bill போடு", "அதுக்கு bill போடு", "bill podu", "பில் போடு")
        # -----------------------------------------------------------------
        if ("bill" in lower or "பில்" in lower) and not ("sales" in lower or "report" in lower or "ethana" in lower or "count" in lower):
            qty_match = re.search(r"(\d+(\.\d+)?)", lower)
            qty = float(qty_match.group(1)) if qty_match else None

            if not prod and not ("adhuku" in lower or "அதுக்கு" in lower):
                return CommandIntent(
                    intent=IntentCategory.SELL_PRODUCT,
                    language="Tamil" if is_tamil_script else "Tanglish",
                    original_text=raw,
                    normalized_text="Create customer bill (product unspecified)",
                    entities=CommandEntities(product_name=None, quantity=qty, unit=unit),
                    confidence=0.94,
                    requires_clarification=True,
                    clarification_question="எந்தப் பொருளுக்கு பில் போட வேண்டும்?" if is_tamil_script else "Endha product-ku bill podanum?",
                )

            if prod and qty is None:
                q_text = f"{prod_ta or prod} எவ்வளவு வேண்டும்?" if is_tamil_script else f"{prod} evlo venum?"
                return CommandIntent(
                    intent=IntentCategory.SELL_PRODUCT,
                    language="Tamil" if is_tamil_script else "Tanglish",
                    original_text=raw,
                    normalized_text=f"Create bill for {prod} (quantity missing)",
                    entities=CommandEntities(product_name=prod, quantity=None, unit=unit),
                    confidence=0.95,
                    requires_clarification=True,
                    clarification_question=q_text,
                )

            return CommandIntent(
                intent=IntentCategory.SELL_PRODUCT,
                language="Tamil" if is_tamil_script else "Tanglish",
                original_text=raw,
                normalized_text=f"Record sale of {qty} {unit} {prod or 'active item'}",
                entities=CommandEntities(product_name=prod, quantity=qty, unit=unit, payment_method="CASH"),
                confidence=0.96,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 4: CHECK_STOCK (Read-only stock inquiry in Tamil, Tanglish, or English)
        # "அரிசி stock எவ்வளவு?", "Rice stock evlo irukku?", "How much rice stock do we have?", "Sugar vila evlo?"
        # -----------------------------------------------------------------
        is_check_stock = (
            any(w in lower for w in [
                "evlo irukku", "இருப்பு எவ்வளவு", "stock check", "check stock",
                "how much", "how many", "do we have", "in stock", "stock evlo",
                "stock எவ்வளவு", "stock இல்லையா", "stock இருக்கா", "இருப்பு",
                "stock details", "current stock", "stock quantity", "available stock",
                "have in stock", "vila evlo", "vilai evlo", "விலை எவ்வளவு", "price evlo", "rate evlo"
            ])
            and "sales" not in lower
            and not ("add" in lower or "சேர்க்க" in lower or "சேரு" in lower or "vandhirukku" in lower or "bill" in lower or "sale" in lower)
        )
        if is_check_stock:
            prod = prod or "Ponni Boiled Rice"
            return CommandIntent(
                intent=IntentCategory.CHECK_STOCK,
                language=detected_lang,
                original_text=raw,
                normalized_text=f"Check current inventory for {prod}",
                entities=CommandEntities(product_name=prod),
                confidence=0.98,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 5: ADD_STOCK
        # "ரெண்டு கிலோ அரிசி ஸ்டாக் சேர்த்திடு", "10 kilo godhumai maavu stock add pannunga", "Add 5 kg rice to inventory"
        # -----------------------------------------------------------------
        is_add_stock = (
            "add" in lower
            or "சேர்க்க" in lower
            or "சேர்த்திடு" in lower
            or "சேர்த்து" in lower
            or "சேர்" in lower
            or "vandhirukku" in lower
            or "received" in lower
            or (
                ("stock" in lower or "ஸ்டாக்" in lower)
                and not any(k in lower for k in [
                    "check", "evlo", "sales", "kammi", "low", "report", "best",
                    "top", "ethana", "sollu", "இல்லையா", "இருக்கா", "எவ்வளவு",
                    "remove", "korainga", "கழி", "set", "adjust", "update", "value"
                ])
            )
        )
        if is_add_stock and not any(kw in lower for kw in ["new product", "pudhu product", "remove", "korainga"]):
            prod = prod or "Ponni Boiled Rice"

            qty_match = re.search(r"(\d+(\.\d+)?)", lower)
            if not qty_match:
                q_text = f"எவ்வளவு {prod_ta or prod} சேர்க்க வேண்டும்?" if is_tamil_script else f"Evlo {unit} {prod} add pannanum?"
                return CommandIntent(
                    intent=IntentCategory.ADD_STOCK,
                    language=detected_lang,
                    original_text=raw,
                    normalized_text=f"Add {prod} to stock (quantity missing)",
                    entities=CommandEntities(product_name=prod, quantity=None, unit=unit),
                    confidence=0.95,
                    requires_clarification=True,
                    clarification_question=q_text,
                )

            qty = float(qty_match.group(1))

            return CommandIntent(
                intent=IntentCategory.ADD_STOCK,
                language=detected_lang,
                original_text=raw,
                normalized_text=f"Add {qty} {unit} {prod} to inventory",
                entities=CommandEntities(product_name=prod, quantity=qty, unit=unit),
                confidence=0.98,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 5B: REMOVE_STOCK
        # "Rice 5 kilo remove pannu", "Sugar 5 kilo remove pannu", "Remove 2 kg rice", "கழி"
        # -----------------------------------------------------------------
        if ("remove" in lower or "korainga" in lower or "கழி" in lower) and not ("cancel" in lower or "ரத்து" in lower):
            prod = prod or "Ponni Boiled Rice"
            qty_match = re.search(r"(\d+(\.\d+)?)", lower)
            qty = float(qty_match.group(1)) if qty_match else 1.0

            return CommandIntent(
                intent=IntentCategory.REMOVE_STOCK,
                language=detected_lang,
                original_text=raw,
                normalized_text=f"Remove {qty} {unit} {prod} from stock",
                entities=CommandEntities(product_name=prod, quantity=qty, unit=unit),
                confidence=0.98,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 5C: SET_STOCK (Adjust verified physical stock)
        # "Rice stock 50 kg set pannu", "Set tomato stock to 20 kg"
        # -----------------------------------------------------------------
        if ("set" in lower or "adjust" in lower or "update" in lower or "irukku nu update" in lower) and ("stock" in lower or "இருப்பு" in lower) and not ("price" in lower or "rate" in lower or "vilai" in lower or "விலை" in lower):
            prod = prod or "Ponni Boiled Rice"
            qty_match = re.search(r"(\d+(\.\d+)?)", lower)
            qty = float(qty_match.group(1)) if qty_match else 10.0

            return CommandIntent(
                intent=IntentCategory.SET_STOCK,
                language=detected_lang,
                original_text=raw,
                normalized_text=f"Set verified physical stock for {prod} to {qty} {unit}",
                entities=CommandEntities(product_name=prod, quantity=qty, unit=unit),
                confidence=0.98,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 6: SELL_PRODUCT (Single Item or Fragmented e.g. "Tomato one kg", "தக்காளி ஒரு கிலோ")
        # -----------------------------------------------------------------
        if ("sell" in lower or "sale" in lower or "விற்று" in lower or "விற்பனை" in lower or "kuduthuten" in lower or (prod and re.search(r"\d+(\.\d+)?", lower))) and not ("evlo" in lower or "ethana" in lower or "report" in lower or "best" in lower or "top" in lower or "count" in lower or "எவ்வளவு" in lower or "இல்லையா" in lower or "stock" in lower):
            prod = prod or "Ponni Boiled Rice"

            qty_match = re.search(r"(\d+(\.\d+)?)", lower)
            qty = float(qty_match.group(1)) if qty_match else 1.0

            return CommandIntent(
                intent=IntentCategory.SELL_PRODUCT,
                language=detected_lang,
                original_text=raw,
                normalized_text=f"Record sale of {qty} {unit} {prod}",
                entities=CommandEntities(product_name=prod, quantity=qty, unit=unit, payment_method="CASH"),
                confidence=0.96,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 7: LOW_STOCK_QUERY & REORDER INTELLIGENCE
        # "Low stock products sollu", "Naalaikku entha products stock out aagum?", "What should I reorder tomorrow?", "குறைந்த இருப்பு"
        # -----------------------------------------------------------------
        if any(kw in lower for kw in ["kammi", "low stock", "குறைந்த", "out of stock", "stock out", "naalaikku", "reorder", "running low", "தீர்ந்துபோகும்"]):
            return CommandIntent(
                intent=IntentCategory.LOW_STOCK_QUERY,
                language="Tamil" if is_tamil_script else "Tanglish",
                original_text=raw,
                normalized_text="List low stock and future stock-out reorder intelligence",
                entities=CommandEntities(),
                confidence=0.98,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 8: BEST SELLING PRODUCT REPORT
        # "Innaiku best selling product enna?", "Top selling product"
        # -----------------------------------------------------------------
        if "best sell" in lower or "top sell" in lower or "best selling" in lower:
            return CommandIntent(
                intent=IntentCategory.PRODUCT_SALES_REPORT,
                language="Tamil" if is_tamil_script else "Tanglish",
                original_text=raw,
                normalized_text="Show today's best selling product",
                entities=CommandEntities(date="today"),
                confidence=0.98,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 9: SALES_REPORT & BILL COUNT
        # "Innaiku sales evlo?", "Innaiku ethana bill potten?", "இன்றைய விற்பனை எவ்வளவு?", "இன்னைக்கு sales எவ்வளவு?"
        # -----------------------------------------------------------------
        if "sales evlo" in lower or "விற்பனை எவ்வளவு" in lower or "today sales" in lower or "innaiku sales" in lower or "ethana bill" in lower or "bill count" in lower or "sales எவ்வளவு" in lower or "விற்பனை" in lower:
            return CommandIntent(
                intent=IntentCategory.SALES_REPORT,
                language="Tamil" if is_tamil_script else "Tanglish",
                original_text=raw,
                normalized_text="Show today sales revenue and bill count",
                entities=CommandEntities(date="today"),
                confidence=0.98,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 9B: INVENTORY_REPORT
        # "Total inventory value evlo?", "Inventory valuation", "மொத்த இருப்பு மதிப்பு"
        # -----------------------------------------------------------------
        if "inventory" in lower or "இருப்பு மதிப்பு" in lower or "stock value" in lower:
            return CommandIntent(
                intent=IntentCategory.INVENTORY_REPORT,
                language="Tamil" if is_tamil_script else "Tanglish",
                original_text=raw,
                normalized_text="Calculate total inventory valuation across active catalog",
                entities=CommandEntities(),
                confidence=0.98,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 10: UPDATE_PRICE
        # -----------------------------------------------------------------
        if ("price" in lower or "rate" in lower or "vilai" in lower or "விலை" in lower) and ("maathu" in lower or "update" in lower or "set" in lower or "podu" in lower or "change" in lower or "rupees" in lower or "ரூபாய்" in lower):
            prod = prod or "Ponni Boiled Rice"
            price_match = re.search(r"(\d+(\.\d+)?)", lower)
            price_val = float(price_match.group(1)) if price_match else None

            return CommandIntent(
                intent=IntentCategory.UPDATE_PRICE,
                language="Tamil" if is_tamil_script else "Tanglish",
                original_text=raw,
                normalized_text=f"Update selling price for {prod} to ₹{price_val}",
                entities=CommandEntities(product_name=prod, price=price_val, quantity=price_val),
                confidence=0.97,
                requires_clarification=False if price_val else True,
                clarification_question=None if price_val else (f"{prod_ta or prod} விலை எவ்வளவு ரூபாய்?" if is_tamil_script else f"{prod} selling price evlo rupees?"),
            )

        # -----------------------------------------------------------------
        # Pattern 11: CREATE_PRODUCT
        # -----------------------------------------------------------------
        if ("new product" in lower or "pudhu product" in lower or "add product" in lower or "புது பொருள்" in lower or "register product" in lower):
            cleaned = lower
            for fw in ["new product", "pudhu product", "add product", "register product", "add", "pannunga", "podunga", "please"]:
                cleaned = re.sub(r"\b" + re.escape(fw) + r"\b", "", cleaned)
            price_match = re.search(r"(\d+(\.\d+)?)", cleaned)
            price_val = float(price_match.group(1)) if price_match else 50.0
            cleaned = re.sub(r"(\d+(\.\d+)?)", "", cleaned)
            for w in ["rupees", "rs", "kilo", "kg", "litre", "per", "விலை", "ரூபாய்"]:
                cleaned = re.sub(r"\b" + re.escape(w) + r"\b", "", cleaned)
            prod_name = cleaned.strip().title() or "New Item"

            unit = "kg"
            if "litre" in lower or "லிட்டர்" in lower:
                unit = "litre"
            elif "packet" in lower or "பாக்கெட்" in lower:
                unit = "packet"

            return CommandIntent(
                intent=IntentCategory.CREATE_PRODUCT,
                language="Tamil" if is_tamil_script else "Tanglish",
                original_text=raw,
                normalized_text=f"Register new product {prod_name} at ₹{price_val}/{unit}",
                entities=CommandEntities(product_name=prod_name, price=price_val, quantity=price_val, unit=unit),
                confidence=0.96,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Default / Fallback — Tamil-First, Never Generic "I could not understand"
        # -----------------------------------------------------------------
        if is_tamil_script:
            fallback_q = "மன்னிக்கவும், எந்தப் பொருளைப் பற்றி சொல்கிறீர்கள்?"
        elif lower.isascii() and not any(k in lower for k in ["pannu", "podu", "evlo", "seri", "aama", "kodu"]):
            fallback_q = "Sorry, which product are you referring to?"
        else:
            fallback_q = "மன்னிக்கவும், எந்தப் பொருளைப் பற்றி சொல்கிறீர்கள்?"

        return CommandIntent(
            intent=IntentCategory.UNKNOWN,
            language="Tamil" if is_tamil_script else "Tanglish",
            original_text=raw,
            normalized_text="Query requiring clarification",
            entities=CommandEntities(),
            confidence=0.6,
            requires_clarification=True,
            clarification_question=fallback_q,
        )


class GeminiIntentProvider(IntentProvider):
    """Live Google Gemini Intent Provider."""

    async def extract_intent(self, text: str) -> CommandIntent:
        from backend.app.services.gemini_client import gemini_client
        return await gemini_client.generate_intent_async(text)


# =============================================================================
# 3. TEXT-TO-SPEECH (TTS) PROVIDER INTERFACE
# =============================================================================

class TTSProvider(ABC):
    """Abstract interface for Speech Audio Synthesis."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        language: str = "ta-IN",
        speed: float = 1.0,
        voice: str = "standard",
    ) -> Tuple[bytes, str, str]:
        pass


class MockTTSProvider(TTSProvider):
    """Deterministic Mock TTS Provider: Generates valid PCM WAV speech audio."""

    async def synthesize(
        self,
        text: str,
        language: str = "ta-IN",
        speed: float = 1.0,
        voice: str = "standard",
    ) -> Tuple[bytes, str, str]:
        from backend.app.services.gnani_tts_service import gnani_tts_service
        audio = gnani_tts_service._generate_mock_wav(duration=1.2, freq=520.0)
        return audio, "audio/wav", "mock_timbre"


class GnaniTimbreTTSProvider(TTSProvider):
    """Live Gnani Timbre v2.5 TTS REST Provider."""

    async def synthesize(
        self,
        text: str,
        language: str = "ta-IN",
        speed: float = 1.0,
        voice: str = "standard",
    ) -> Tuple[bytes, str, str]:
        from backend.app.services.gnani_tts_service import gnani_tts_service
        return await gnani_tts_service.synthesize_speech(
            text=text,
            language=language,
            speed=speed,
            voice=voice,
        )


# =============================================================================
# 4. PROVIDER FACTORY HELPERS
# =============================================================================

_mock_stt = MockSTTProvider()
_gnani_stt = GnaniPrismaSTTProvider()

_mock_intent = MockIntentProvider()
_gemini_intent = GeminiIntentProvider()

_mock_tts = MockTTSProvider()
_gnani_tts = GnaniTimbreTTSProvider()


def get_stt_provider() -> STTProvider:
    if settings.is_gnani_stt_ready:
        return _gnani_stt
    return _mock_stt


def get_intent_provider() -> IntentProvider:
    if settings.is_gemini_ready:
        return _gemini_intent
    return _mock_intent


def get_tts_provider() -> TTSProvider:
    if settings.is_gnani_tts_ready:
        return _gnani_tts
    return _mock_tts
