"""Store & Voice Settings Pydantic Schemas with Indian & International Phone Validation."""
import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


def validate_phone_number(v: Optional[str]) -> Optional[str]:
    """Validate Indian 10-digit or valid international phone format."""
    if not v or not v.strip():
        return None
    cleaned = v.strip()
    # Normalize spaces, dashes, parentheses
    digits = re.sub(r"[^\d+]", "", cleaned)
    # Check minimum length (e.g. 10 digits for Indian standard)
    if digits.startswith("+"):
        pure_digits = digits[1:]
    else:
        pure_digits = digits

    if len(pure_digits) < 10 or len(pure_digits) > 15:
        raise ValueError("Phone number must contain between 10 and 15 digits.")
    return cleaned


class StoreSettingsBase(BaseModel):
    shop_name: str = Field(..., min_length=1, max_length=150, description="Shop display name in English")
    shop_name_ta: Optional[str] = Field(None, max_length=150, description="Shop display name in Tamil")
    owner_name: str = Field(..., min_length=1, max_length=100, description="Store proprietor name")
    phone: str = Field(..., min_length=10, max_length=30, description="Shop contact phone")
    whatsapp_number: Optional[str] = Field(None, max_length=30, description="WhatsApp contact number")
    address: Optional[str] = Field(None, max_length=500, description="Physical store address")
    email: Optional[str] = Field(None, max_length=100, description="Store contact email")
    gstin: Optional[str] = Field(None, max_length=30, description="GSTIN tax registration number")
    currency: str = Field("INR", max_length=10, description="Store operating currency")
    currency_symbol: str = Field("₹", max_length=10, description="Currency display symbol")
    preferred_language: str = Field("ta", max_length=10, description="Preferred interface language (ta, en, etc.)")
    voice_preferred_language: str = Field("ta", max_length=20, description="Preferred voice language (ta, tanglish, en)")
    speech_speed: float = Field(1.0, ge=0.5, le=2.0, description="Text-to-speech audio speed rate")
    auto_speak_responses: bool = Field(True, description="Whether to automatically play synthesized Tamil speech")
    low_stock_threshold_default: float = Field(5.0, ge=1.0, description="Default product low stock threshold")
    receipt_footer: Optional[str] = Field("நன்றி! மீண்டும் வருக! / Thank you, visit again!", description="Printed receipt footer note")

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        res = validate_phone_number(v)
        if not res:
            raise ValueError("Contact phone cannot be empty.")
        return res

    @field_validator("whatsapp_number")
    @classmethod
    def check_whatsapp(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_number(v)

    @field_validator("email")
    @classmethod
    def check_email(cls, v: Optional[str]) -> Optional[str]:
        if not v or not v.strip():
            return None
        cleaned = v.strip()
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", cleaned):
            raise ValueError("Invalid email address format.")
        return cleaned


class StoreSettingsUpdate(BaseModel):
    shop_name: Optional[str] = Field(None, min_length=1, max_length=150)
    shop_name_ta: Optional[str] = None
    owner_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    gstin: Optional[str] = None
    currency: Optional[str] = None
    currency_symbol: Optional[str] = None
    preferred_language: Optional[str] = None
    voice_preferred_language: Optional[str] = None
    speech_speed: Optional[float] = None
    auto_speak_responses: Optional[bool] = None
    low_stock_threshold_default: Optional[float] = None
    receipt_footer: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            res = validate_phone_number(v)
            if not res:
                raise ValueError("Contact phone cannot be empty if specified.")
            return res
        return v

    @field_validator("whatsapp_number")
    @classmethod
    def check_whatsapp(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_phone_number(v)
        return v

    @field_validator("email")
    @classmethod
    def check_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            cleaned = v.strip()
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", cleaned):
                raise ValueError("Invalid email address format.")
            return cleaned
        return None if v is not None and not v.strip() else v


class StoreSettingsResponse(StoreSettingsBase):
    id: int = 1
    gemini_ready: bool = False
    gnani_stt_ready: bool = False
    gnani_tts_ready: bool = False
    active_env: str = "production"
