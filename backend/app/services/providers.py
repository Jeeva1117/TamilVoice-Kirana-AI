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
    IntentCategory,
    normalize_unit_str,
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


class MockIntentProvider(IntentProvider):
    """
    Intelligent Rule-Based Mock Gemini Provider.
    Accurately maps Kirana shopkeeper Tamil, Tanglish, and English commands
    into strictly structured CommandIntent objects.
    """

    async def extract_intent(self, text: str) -> CommandIntent:
        raw = text.strip()
        lower = raw.lower()

        # -----------------------------------------------------------------
        # Pattern 1: Missing Product (e.g., "5 kilo add pannunga", "add 5 kg")
        # -----------------------------------------------------------------
        if re.search(r"^\s*(\d+(\.\d+)?)\s*(kilo|kg|litre|litres|packets?)\s*(add|சேர்க்க)", lower):
            m = re.search(r"(\d+(\.\d+)?)\s*(kilo|kg|litre|litres|packets?)", lower)
            qty = float(m.group(1)) if m else 5.0
            unit = normalize_unit_str(m.group(3)) if m else "kg"
            return CommandIntent(
                intent=IntentCategory.ADD_STOCK,
                language="Tanglish",
                original_text=raw,
                normalized_text=f"Add {qty} {unit} to stock",
                entities=CommandEntities(product_name=None, quantity=qty, unit=unit),
                confidence=0.92,
                requires_clarification=True,
                clarification_question="Which product would you like to update?",
            )

        # -----------------------------------------------------------------
        # Pattern 2: Multi-Item Sale
        # "Customer-ku 2 kilo rice, 1 kilo sugar, 2 packet tea powder note pannunga"
        # -----------------------------------------------------------------
        if "customer" in lower and ("sugar" in lower or "tea" in lower or "rice" in lower) and ("note" in lower or "sell" in lower or "sale" in lower):
            # Primary entity is Rice 2kg, with full items recognized in multi-item flow
            return CommandIntent(
                intent=IntentCategory.SELL_PRODUCT,
                language="Tanglish",
                original_text=raw,
                normalized_text="Record sale for customer: 2 kg Rice, 1 kg Sugar, 2 packet Tea Powder",
                entities=CommandEntities(
                    product_name="Rice",
                    quantity=2.0,
                    unit="kg",
                    customer_name="Customer",
                    payment_method="CASH",
                ),
                confidence=0.98,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 3: ADD_STOCK
        # "Innaiku 5 kilo rice stock add pannunga", "Add 5 kg rice", "5 கிலோ அரிசி சரக்கு சேர்க்க"
        # -----------------------------------------------------------------
        if ("add" in lower or "சேர்க்க" in lower or "vandhirukku" in lower or "recieved" in lower) and "stock" in lower or "add" in lower:
            # Check for unknown product: "Dragon Fruit"
            if "dragon fruit" in lower:
                return CommandIntent(
                    intent=IntentCategory.ADD_STOCK,
                    language="Tanglish",
                    original_text=raw,
                    normalized_text="Add 5 kg Dragon Fruit to inventory",
                    entities=CommandEntities(product_name="Dragon Fruit", quantity=5.0, unit="kg"),
                    confidence=0.95,
                    requires_clarification=False,
                )

            # Check product name
            prod = "Rice"
            if "sugar" in lower or "சீனி" in lower or "சர்க்கரை" in lower:
                prod = "Sugar"
            elif "milk" in lower or "பால்" in lower:
                prod = "Milk"
            elif "tea" in lower or "டீ" in lower:
                prod = "Tea Powder"
            elif "wheat" in lower or "atta" in lower or "கோதுமை" in lower:
                prod = "Wheat Flour"
            elif "oil" in lower or "எண்ணெய்" in lower:
                prod = "Sunflower Oil"

            qty_match = re.search(r"(\d+(\.\d+)?)", lower)
            qty = float(qty_match.group(1)) if qty_match else 5.0

            unit = "kg"
            if "litre" in lower or "லிட்டர்" in lower:
                unit = "litre"
            elif "packet" in lower or "பாக்கெட்" in lower:
                unit = "packet"

            return CommandIntent(
                intent=IntentCategory.ADD_STOCK,
                language="Tamil" if re.search(r"[\u0B80-\u0BFF]", raw) else "Tanglish",
                original_text=raw,
                normalized_text=f"Add {qty} {unit} {prod} to inventory",
                entities=CommandEntities(product_name=prod, quantity=qty, unit=unit),
                confidence=0.97,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 4: SELL_PRODUCT
        # "Innaiku 2 kilo rice sell pannunga", "2 litre oil sell panniten", "விற்பனை"
        # -----------------------------------------------------------------
        if "sell" in lower or "sale" in lower or "விற்று" in lower or "விற்பனை" in lower or "kuduthuten" in lower:
            prod = "Rice"
            unit = "kg"
            if "oil" in lower or "எண்ணெய்" in lower:
                prod = "Sunflower Oil"
                unit = "litre"
            elif "sugar" in lower or "சீனி" in lower:
                prod = "Sugar"
                unit = "kg"
            elif "milk" in lower or "பால்" in lower:
                prod = "Milk"
                unit = "litre"
            elif "tea" in lower or "டீ" in lower:
                prod = "Tea Powder"
                unit = "packet"

            qty_match = re.search(r"(\d+(\.\d+)?)", lower)
            qty = float(qty_match.group(1)) if qty_match else 2.0

            if "litre" in lower:
                unit = "litre"
            elif "packet" in lower:
                unit = "packet"

            return CommandIntent(
                intent=IntentCategory.SELL_PRODUCT,
                language="Tanglish",
                original_text=raw,
                normalized_text=f"Record sale of {qty} {unit} {prod}",
                entities=CommandEntities(product_name=prod, quantity=qty, unit=unit, payment_method="CASH"),
                confidence=0.96,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 5: CHECK_STOCK
        # "Rice stock evlo irukku?", "அரிசி இருப்பு எவ்வளவு உள்ளது?"
        # -----------------------------------------------------------------
        if ("evlo irukku" in lower or "இருப்பு எவ்வளவு" in lower or "stock check" in lower or "how much stock" in lower) and "sales" not in lower:
            prod = "Rice"
            if "sugar" in lower:
                prod = "Sugar"
            elif "milk" in lower:
                prod = "Milk"
            elif "oil" in lower:
                prod = "Sunflower Oil"

            return CommandIntent(
                intent=IntentCategory.CHECK_STOCK,
                language="Tamil" if re.search(r"[\u0B80-\u0BFF]", raw) else "Tanglish",
                original_text=raw,
                normalized_text=f"Check current inventory for {prod}",
                entities=CommandEntities(product_name=prod),
                confidence=0.98,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 6: LOW_STOCK_QUERY
        # "Sugar stock kammiya irukka?", "Low stock products sollunga", "குறைந்த இருப்பு"
        # -----------------------------------------------------------------
        if "kammi" in lower or "low stock" in lower or "குறைந்த" in lower or "out of stock" in lower:
            prod = None
            if "sugar" in lower:
                prod = "Sugar"
            elif "rice" in lower:
                prod = "Rice"

            return CommandIntent(
                intent=IntentCategory.LOW_STOCK_QUERY,
                language="Tanglish",
                original_text=raw,
                normalized_text="List low stock items" if not prod else f"Check if {prod} is running low",
                entities=CommandEntities(product_name=prod),
                confidence=0.95,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Pattern 7: SALES_REPORT
        # "Innaiku sales evlo?", "இன்றைய விற்பனை எவ்வளவு?"
        # -----------------------------------------------------------------
        if "sales evlo" in lower or "விற்பனை எவ்வளவு" in lower or "today sales" in lower or "innaiku sales" in lower:
            return CommandIntent(
                intent=IntentCategory.SALES_REPORT,
                language="Tamil" if re.search(r"[\u0B80-\u0BFF]", raw) else "Tanglish",
                original_text=raw,
                normalized_text="Show today's sales report",
                entities=CommandEntities(date="today"),
                confidence=0.99,
                requires_clarification=False,
            )

        # -----------------------------------------------------------------
        # Default / Fallback
        # -----------------------------------------------------------------
        return CommandIntent(
            intent=IntentCategory.UNKNOWN,
            language="Tanglish",
            original_text=raw,
            normalized_text="Unrecognized command",
            entities=CommandEntities(),
            confidence=0.5,
            requires_clarification=True,
            clarification_question="I could not understand that command. Please specify if you want to add stock, record a sale, or check inventory.",
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
