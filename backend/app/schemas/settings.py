"""Store & Voice Settings Pydantic Schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class StoreSettingsBase(BaseModel):
    shop_name: str = Field("Karthik Kirana Store", description="Shop display name in English")
    shop_name_ta: str = Field("கார்த்திக் மளிகைக் கடை", description="Shop display name in Tamil")
    owner_name: str = Field("Karthikeyan R.", description="Store proprietor name")
    phone: str = Field("+91 98401 23456", description="Shop contact phone")
    address: str = Field("42, North Mada Street, Mylapore, Chennai, Tamil Nadu - 600004", description="Physical store address")
    gstin: Optional[str] = Field("33ABCDE1234F1Z5", description="GSTIN tax registration number")
    currency: str = Field("INR", description="Store operating currency")
    currency_symbol: str = Field("₹", description="Currency display symbol")
    timezone: str = Field("Asia/Kolkata", description="Store business timezone")
    voice_preferred_language: str = Field("ta", description="Preferred voice language (ta, tanglish, en)")
    speech_speed: float = Field(1.0, ge=0.5, le=2.0, description="Text-to-speech audio speed rate")
    auto_speak_responses: bool = Field(True, description="Whether to automatically play synthesized Tamil speech")
    low_stock_threshold_default: float = Field(5.0, ge=1.0, description="Default product low stock threshold")
    receipt_footer: str = Field("நன்றி! மீண்டும் வருக! / Thank you, visit again!", description="Printed receipt footer note")


class StoreSettingsUpdate(BaseModel):
    shop_name: Optional[str] = None
    shop_name_ta: Optional[str] = None
    owner_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gstin: Optional[str] = None
    currency: Optional[str] = None
    currency_symbol: Optional[str] = None
    timezone: Optional[str] = None
    voice_preferred_language: Optional[str] = None
    speech_speed: Optional[float] = None
    auto_speak_responses: Optional[bool] = None
    low_stock_threshold_default: Optional[float] = None
    receipt_footer: Optional[str] = None


class StoreSettingsResponse(StoreSettingsBase):
    gemini_ready: bool = False
    gnani_stt_ready: bool = False
    gnani_tts_ready: bool = False
    active_env: str = "production"

