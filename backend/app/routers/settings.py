"""Settings Router: Manage Kirana store profile, billing rules, and voice configuration in SQLite/PostgreSQL database."""
import os
import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import get_db, engine, Base
from backend.app.models.store_setting import StoreSetting
from backend.app.schemas.settings import (
    StoreSettingsBase,
    StoreSettingsUpdate,
    StoreSettingsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings"])

DEFAULT_STORE_DATA: Dict[str, Any] = {
    "shop_name": "Arjun Grocery Store",
    "shop_name_ta": "அர்ஜுன் மளிகைக் கடை",
    "owner_name": "Jeevan",
    "phone": "+91 98401 23456",
    "whatsapp_number": "+91 98401 23456",
    "address": "42, North Mada Street, Mylapore, Chennai, Tamil Nadu - 600004",
    "email": "contact@arjungrocery.in",
    "gstin": "33ABCDE1234F1Z5",
    "currency": "INR",
    "currency_symbol": "₹",
    "preferred_language": "ta",
    "voice_preferred_language": "ta",
    "speech_speed": 1.0,
    "auto_speak_responses": True,
    "low_stock_threshold_default": 5.0,
    "receipt_footer": "நன்றி! மீண்டும் வருக! / Thank you, visit again!",
}


def get_or_create_settings(db: Session) -> StoreSetting:
    """Ensure a single authoritative store setting record exists in DB."""
    # Ensure tables are created
    Base.metadata.create_all(bind=engine)
    record = db.query(StoreSetting).order_by(StoreSetting.id.asc()).first()
    if not record:
        record = StoreSetting(**DEFAULT_STORE_DATA)
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


def _load_settings() -> Dict[str, Any]:
    """Backward-compatible helper to load store settings dict from DB."""
    from backend.app.database import SessionLocal
    db = SessionLocal()
    try:
        current = get_or_create_settings(db)
        return {
            "shop_name": current.shop_name,
            "shop_name_ta": current.shop_name_ta,
            "owner_name": current.owner_name,
            "phone": current.phone,
            "whatsapp_number": current.whatsapp_number,
            "address": current.address,
            "email": current.email,
            "gstin": current.gstin,
            "currency": current.currency,
            "currency_symbol": current.currency_symbol,
            "preferred_language": current.preferred_language,
            "voice_preferred_language": current.voice_preferred_language,
            "speech_speed": current.speech_speed,
            "auto_speak_responses": current.auto_speak_responses,
            "low_stock_threshold_default": current.low_stock_threshold_default,
            "receipt_footer": current.receipt_footer,
        }
    finally:
        db.close()


def _save_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    """Backward-compatible helper to update store settings dict in DB."""
    from backend.app.database import SessionLocal
    db = SessionLocal()
    try:
        current = get_or_create_settings(db)
        for k, v in data.items():
            if hasattr(current, k) and v is not None:
                setattr(current, k, v)
        db.commit()
        db.refresh(current)
        return _load_settings()
    finally:
        db.close()


@router.get("", response_model=StoreSettingsResponse)
def get_store_settings(db: Session = Depends(get_db)):
    """Retrieve active Kirana store details from database."""
    current = get_or_create_settings(db)
    
    return StoreSettingsResponse(
        id=current.id,
        shop_name=current.shop_name,
        shop_name_ta=current.shop_name_ta,
        owner_name=current.owner_name,
        phone=current.phone,
        whatsapp_number=current.whatsapp_number,
        address=current.address,
        email=current.email,
        gstin=current.gstin,
        currency=current.currency,
        currency_symbol=current.currency_symbol,
        preferred_language=current.preferred_language,
        voice_preferred_language=current.voice_preferred_language,
        speech_speed=current.speech_speed,
        auto_speak_responses=current.auto_speak_responses,
        low_stock_threshold_default=current.low_stock_threshold_default,
        receipt_footer=current.receipt_footer,
        gemini_ready=settings.is_gemini_ready,
        gnani_stt_ready=settings.is_gnani_stt_ready,
        gnani_tts_ready=settings.is_gnani_tts_ready,
        active_env="debug" if settings.DEBUG else "production",
    )


@router.put("", response_model=StoreSettingsResponse)
def update_store_settings(settings_in: StoreSettingsUpdate, db: Session = Depends(get_db)):
    """Update store details, contact, and operational parameters in database."""
    current = get_or_create_settings(db)
    updates = settings_in.model_dump(exclude_unset=True)

    for field, val in updates.items():
        if hasattr(current, field) and val is not None:
            setattr(current, field, val)

    db.add(current)
    db.commit()
    db.refresh(current)

    return StoreSettingsResponse(
        id=current.id,
        shop_name=current.shop_name,
        shop_name_ta=current.shop_name_ta,
        owner_name=current.owner_name,
        phone=current.phone,
        whatsapp_number=current.whatsapp_number,
        address=current.address,
        email=current.email,
        gstin=current.gstin,
        currency=current.currency,
        currency_symbol=current.currency_symbol,
        preferred_language=current.preferred_language,
        voice_preferred_language=current.voice_preferred_language,
        speech_speed=current.speech_speed,
        auto_speak_responses=current.auto_speak_responses,
        low_stock_threshold_default=current.low_stock_threshold_default,
        receipt_footer=current.receipt_footer,
        gemini_ready=settings.is_gemini_ready,
        gnani_stt_ready=settings.is_gnani_stt_ready,
        gnani_tts_ready=settings.is_gnani_tts_ready,
        active_env="debug" if settings.DEBUG else "production",
    )
