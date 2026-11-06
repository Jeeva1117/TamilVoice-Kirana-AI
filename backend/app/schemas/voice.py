"""Voice Processing Pydantic Schemas."""
from typing import Optional
from pydantic import BaseModel


class VoiceProcessRequest(BaseModel):
    transcript: Optional[str] = None
    language: str = "ta"


class VoiceProcessResponse(BaseModel):
    transcript: str
    action: str
    action_ta: str
    product: Optional[str] = None
    product_ta: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    confidence: float
    requires_confirmation: bool
    response_ta: str
    response_tanglish: str
    response_en: str
