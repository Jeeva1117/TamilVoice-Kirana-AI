"""Voice Processing Pydantic Schemas for Gnani Prisma STT and Timbre TTS."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.app.schemas.ai import CommandIntent, ResolvedProduct, ConfirmationPreview


class TranscribeResponse(BaseModel):
    success: bool
    transcript: str
    provider: str  # "gnani_prisma" or "mock_prisma"
    model: str  # "prisma-v2.5"
    language: str = "ta-IN"
    detected_language: Optional[str] = None
    confidence: Optional[float] = None
    is_mock: bool = False
    duration_seconds: Optional[float] = None
    audio_size_bytes: int
    message: str


class VoiceCommandResponse(BaseModel):
    success: bool
    transcript: str
    stt_provider: str
    intent: CommandIntent
    resolved_product: Optional[ResolvedProduct] = None
    candidate_products: List[ResolvedProduct] = Field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_preview: Optional[ConfirmationPreview] = None
    query_result: Optional[Dict[str, Any]] = None
    message: str
    message_ta: Optional[str] = None
    message_tanglish: Optional[str] = None
    detected_language: Optional[str] = "Tamil"
    spoken_response: Optional[str] = None
    stage_error: Optional[str] = None
    tts_available: bool = True
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    audio_url: Optional[str] = None


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, description="Text to synthesize into speech")
    language: str = Field("ta-IN", description="Tamil or target Indian language identifier")
    model: str = Field("timbre-v2.5", description="Gnani Timbre model identifier")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Audio playback speed multiplier")
    voice: Optional[str] = Field("Nalini", description="Voice profile identifier (e.g. Nalini, Chitra, Deepak)")


class VoiceStatusResponse(BaseModel):
    stt_enabled: bool
    stt_configured: bool
    stt_ready: bool = False
    stt_model: str
    tts_enabled: bool
    tts_configured: bool
    tts_ready: bool = False
    tts_model: str
    provider: str = "Gnani Prisma v2.5 & Timbre v2.5"
    provider_base_url: str
    ready: bool
    supported_languages: List[str] = ["ta-IN", "ta", "tanglish", "en-IN", "en"]
    demo_mode: bool = True


# Legacy compatibility
class VoiceProcessRequest(BaseModel):
    command_text: Optional[str] = None
    transcript: Optional[str] = None
    language: str = "ta"


class VoiceProcessResponse(BaseModel):
    success: bool = True
    transcript: str
    action: str
    action_ta: str
    product: Optional[str] = None
    product_ta: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    confidence: float = 0.95
    requires_confirmation: bool = False
    response_ta: str = ""
    response_tanglish: str = ""
    response_en: str = ""
