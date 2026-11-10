"""Voice Assistant Router: Gnani Prisma STT, Timbre TTS, and Voice Pipeline Endpoints."""
import io
import json
import logging
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
from backend.app.services.gnani_usage_tracker import usage_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice Assistant Engine (Gnani + Gemini)"])


@router.get("/usage")
def get_voice_api_usage(db: Session = Depends(get_db)):
    """
    Get audit summary of Gnani API credit usage and testing budget status.
    """
    return usage_tracker.get_summary(db=db)


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
    session_id: Optional[str] = Form(None, description="Conversation session id"),
    context_json: Optional[str] = Form(None, description="Serialized conversation context"),
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

    client_context = None
    if context_json:
        try:
            client_context = json.loads(context_json)
        except Exception:
            pass

    return await voice_service.process_voice_command(
        db=db,
        audio_bytes=audio_bytes,
        transcript_text=text,
        filename=filename,
        content_type=content_type,
        language=language,
        session_id=session_id,
        context=client_context,
    )


@router.post("/speak", status_code=status.HTTP_200_OK)
async def synthesize_assistant_speech(request: SpeakRequest):
    """
    Synthesize assistant text responses into human-like Tamil speech using Gnani Timbre v2.5.
    Returns a binary audio/wav stream playable directly in the browser.
    """
    try:
        audio_bytes, media_type, provider = await gnani_tts_service.synthesize_speech(
            text=request.text,
            language=request.language,
            speed=request.speed,
            voice=request.voice
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Gnani Timbre TTS failed (%s).", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gnani Timbre TTS error: {str(e)}"
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
    language: str = Form("ta-IN"),
    db: Session = Depends(get_db)
):
    """Legacy voice endpoint routed to real production voice service."""
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

    audio_bytes = await audio.read() if audio else None

    # Delegate to real voice pipeline
    res = await voice_service.process_voice_command(
        db=db,
        audio_bytes=audio_bytes,
        transcript_text=raw_transcript if raw_transcript else None,
        language=language,
    )

    action_label = "Add Stock" if res.intent.intent.value == "ADD_STOCK" else ("Record Sale" if res.intent.intent.value == "SELL_PRODUCT" else res.intent.intent.value)
    prod_name = res.resolved_product.name if res.resolved_product else (res.intent.entities.product_name or "General Kirana Item")
    prod_ta = (res.resolved_product.name_ta if res.resolved_product and res.resolved_product.name_ta else None) or (res.intent.entities.product_name or "கிரானா பொருள்")
    qty = res.intent.entities.quantity or 1.0
    unit = res.intent.entities.unit or (res.resolved_product.unit if res.resolved_product else "kg")

    return VoiceProcessResponse(
        success=res.success,
        transcript=res.transcript,
        action=action_label,
        action_ta="சரக்கு சேர்க்க" if "Add" in action_label else "விற்பனை பதிவு",
        product=prod_name,
        product_ta=prod_ta,
        quantity=qty,
        unit=unit,
        confidence=res.intent.confidence,
        requires_confirmation=res.requires_confirmation,
        response_ta=res.message_ta or res.message,
        response_tanglish=res.message,
        response_en=res.message
    )
