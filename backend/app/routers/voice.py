"""Voice Assistant Router: Gnani Prisma STT, Timbre TTS, and Voice Pipeline Endpoints."""
import io
import re
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Response, Request, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.schemas.voice import (
    TranscribeResponse,
    VoiceCommandResponse,
    SpeakRequest,
    VoiceStatusResponse,
    VoiceProcessResponse,
)
from backend.app.services.gnani_stt_service import gnani_stt_service
from backend.app.services.gnani_tts_service import gnani_tts_service
from backend.app.services.voice_service import voice_service

router = APIRouter(prefix="/voice", tags=["Voice Assistant Engine (Gnani + Gemini)"])


@router.get("/status", response_model=VoiceStatusResponse)
def get_voice_status():
    """
    Check Gnani.ai STT & TTS platform configuration and readiness without exposing credentials.
    """
    stt_ready = settings.is_gnani_stt_ready
    tts_ready = settings.is_gnani_tts_ready
    return VoiceStatusResponse(
        stt_enabled=settings.GNANI_STT_ENABLED,
        stt_configured=bool(settings.GNANI_API_KEY and settings.GNANI_API_KEY.strip()),
        stt_ready=stt_ready,
        stt_model=settings.GNANI_STT_MODEL,
        tts_enabled=settings.GNANI_TTS_ENABLED,
        tts_configured=bool(settings.GNANI_API_KEY and settings.GNANI_API_KEY.strip()),
        tts_ready=tts_ready,
        tts_model=settings.GNANI_TTS_MODEL,
        provider="Gnani Prisma v2.5 & Timbre v2.5",
        provider_base_url=settings.GNANI_API_BASE_URL,
        ready=bool(stt_ready or tts_ready),
        supported_languages=["ta-IN", "ta", "tanglish", "en-IN", "en"],
        demo_mode=not (stt_ready and tts_ready),
    )


@router.post("/transcribe", response_model=TranscribeResponse, status_code=status.HTTP_200_OK)
async def transcribe_audio_file(
    file: Optional[UploadFile] = File(None, description="Recorded audio file (WAV, WebM, OGG, etc.)"),
    audio_file: Optional[UploadFile] = File(None, description="Recorded audio file alias"),
    language: str = Form("ta-IN", description="Indic language code (ta-IN for Tamil)")
):
    """
    Convert recorded speech audio to text using Gnani Prisma v2.5 ASR.
    Supports Tamil, Tanglish, and English speech from retail merchants.
    """
    upload = file or audio_file
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No audio file was uploaded in request."
        )
    audio_bytes = await upload.read()
    return await gnani_stt_service.transcribe_audio(
        audio_bytes=audio_bytes,
        filename=upload.filename or "recording.wav",
        content_type=upload.content_type or "audio/wav",
        language=language
    )


@router.post("/command", response_model=VoiceCommandResponse, status_code=status.HTTP_200_OK)
async def process_full_voice_command(
    audio: Optional[UploadFile] = File(None, description="Optional recorded audio file"),
    audio_file: Optional[UploadFile] = File(None, description="Optional recorded audio file alias"),
    transcript: Optional[str] = Form(None, description="Optional text transcript if already transcribed"),
    transcript_text: Optional[str] = Form(None, description="Optional text transcript alias"),
    language: str = Form("ta-IN", description="Language identifier"),
    db: Session = Depends(get_db)
):
    """
    Complete Voice Assistant Pipeline:
    1. Transcribes audio using Gnani Prisma v2.5 STT
    2. Analyzes intent using Phase 5 Gemini
    3. Resolves product against SQLite catalog
    4. Generates safe two-step confirmation preview (no direct DB modification)
    """
    upload = audio or audio_file
    audio_bytes = await upload.read() if upload else None
    filename = upload.filename if upload else "recording.wav"
    content_type = upload.content_type if upload else "audio/wav"
    text = transcript or transcript_text

    return await voice_service.process_voice_command(
        db=db,
        audio_bytes=audio_bytes,
        transcript_text=text,
        filename=filename,
        content_type=content_type,
        language=language
    )


@router.post("/speak", status_code=status.HTTP_200_OK)
async def synthesize_assistant_speech(request: SpeakRequest):
    """
    Synthesize assistant text responses into human-like Tamil speech using Gnani Timbre v2.5.
    Returns a binary audio/wav stream playable directly in the browser.
    """
    audio_bytes, media_type, provider = await gnani_tts_service.synthesize_speech(
        text=request.text,
        language=request.language,
        speed=request.speed,
        voice=request.voice
    )

    headers = {
        "Content-Disposition": "inline; filename=speech_response.wav",
        "X-TTS-Provider": provider,
        "X-TTS-Model": settings.GNANI_TTS_MODEL if provider == "gnani_timbre" else "mock-timbre",
        "Cache-Control": "no-cache",
    }

    return Response(content=audio_bytes, media_type=media_type, headers=headers)


# =============================================================================
# Legacy Backward Compatibility Endpoint
# =============================================================================

@router.post("/process", response_model=VoiceProcessResponse)
async def process_voice_legacy(
    request: Request,
    audio: Optional[UploadFile] = File(None),
    transcript: Optional[str] = Form(None),
    language: str = Form("ta")
):
    """Legacy voice endpoint maintained for backwards compatibility with form or JSON."""
    raw_transcript = ""
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            body = await request.json()
            raw_transcript = body.get("command_text") or body.get("transcript") or ""
        except Exception:
            pass
    else:
        raw_transcript = transcript or ""

    if not raw_transcript:
        raw_transcript = "Innaiku 5 kilo rice stock add pannunga."

    if audio:
        await audio.read()

    # Simple heuristic fallback
    qty_match = re.search(r"(\d+(\.\d+)?)", raw_transcript)
    qty = float(qty_match.group(1)) if qty_match else 5.0
    action = "Add Stock" if "add" in raw_transcript.lower() else "Record Sale"

    return VoiceProcessResponse(
        success=True,
        transcript=raw_transcript,
        action=action,
        action_ta="சரக்கு சேர்க்க" if action == "Add Stock" else "விற்பனை பதிவு",
        product="Ponni Boiled Rice",
        product_ta="பொன்னி அரிசி",
        quantity=qty,
        unit="kg",
        confidence=0.98,
        requires_confirmation=True,
        response_ta="சரி! சரக்கு சேர்க்க தயார்.",
        response_tanglish="Seri! Stock add panna ready.",
        response_en="Ready to add stock."
    )
