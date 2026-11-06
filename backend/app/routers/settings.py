"""Settings Router: Manage Kirana store profile, billing rules, and voice configuration."""
import os
import json
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from backend.app.config import settings
from backend.app.schemas.settings import (
    StoreSettingsBase,
    StoreSettingsUpdate,
    StoreSettingsResponse,
)

router = APIRouter(prefix="/settings", tags=["Settings"])

# Path to persistent local store settings
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "store_settings.json")

DEFAULT_SETTINGS: Dict[str, Any] = {
    "shop_name": "Karthik Kirana Store",
    "shop_name_ta": "கார்த்திக் மளிகைக் கடை",
    "owner_name": "Karthikeyan R.",
    "phone": "+91 98401 23456",
    "address": "42, North Mada Street, Mylapore, Chennai, Tamil Nadu - 600004",
    "gstin": "33ABCDE1234F1Z5",
    "currency": "INR",
    "currency_symbol": "₹",
    "timezone": "Asia/Kolkata",
    "voice_preferred_language": "ta",
    "speech_speed": 1.0,
    "auto_speak_responses": True,
    "low_stock_threshold_default": 5.0,
    "receipt_footer": "நன்றி! மீண்டும் வருக! / Thank you, visit again!",
}


def _load_settings() -> Dict[str, Any]:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                res = DEFAULT_SETTINGS.copy()
                res.update(saved)
                return res
        except Exception:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()


def _save_settings(data: Dict[str, Any]):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


@router.get("", response_model=StoreSettingsResponse)
def get_store_settings():
    """Retrieve active Kirana store details and voice engine status."""
    current = _load_settings()
    return StoreSettingsResponse(
        **current,
        gemini_ready=settings.is_gemini_ready,
        gnani_stt_ready=settings.is_gnani_stt_ready,
        gnani_tts_ready=settings.is_gnani_tts_ready,
        active_env="debug" if settings.DEBUG else "production",
    )


@router.put("", response_model=StoreSettingsResponse)
def update_store_settings(settings_in: StoreSettingsUpdate):
    """Update store details, voice speed, and operational parameters."""
    current = _load_settings()
    updates = settings_in.model_dump(exclude_unset=True)
    current.update(updates)
    _save_settings(current)

    return StoreSettingsResponse(
        **current,
        gemini_ready=settings.is_gemini_ready,
        gnani_stt_ready=settings.is_gnani_stt_ready,
        gnani_tts_ready=settings.is_gnani_tts_ready,
        active_env="debug" if settings.DEBUG else "production",
    )
