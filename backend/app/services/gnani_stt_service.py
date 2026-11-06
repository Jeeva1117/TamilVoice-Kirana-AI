"""Gnani Prisma v2.5 Speech-to-Text (STT) Service.
Verified API integration with https://api.vachana.ai/stt/v3.
"""
import io
import logging
from typing import Optional, Tuple
import httpx
from fastapi import HTTPException, status, UploadFile
from backend.app.config import settings
from backend.app.schemas.voice import TranscribeResponse

logger = logging.getLogger(__name__)

ALLOWED_AUDIO_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp3",
    "audio/flac",
    "application/octet-stream",
}


class VoiceSTTError(HTTPException):
    """Voice Speech-to-Text Exception."""
    def __init__(self, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR, detail: str = ""):
        super().__init__(status_code=status_code, detail=detail)
        self.message = detail


class GnaniSTTService:
    """Service to transcribe Tamil/Tanglish/English voice recordings using Gnani Prisma v2.5."""

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: str = "recording.wav",
        content_type: str = "audio/wav",
        language: str = "ta-IN"
    ) -> TranscribeResponse:
        """
        Transcribe audio using Gnani Prisma STT REST API or fallback to mock when unconfigured.
        """
        # 1. Validation
        size = len(audio_bytes)
        if size == 0:
            raise VoiceSTTError(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty audio payload received. Please record speech before submitting."
            )

        if size < 200:
            raise VoiceSTTError(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio recording is too short or silent. Please speak into the microphone."
            )

        if size > settings.MAX_AUDIO_SIZE_BYTES:
            max_mb = settings.MAX_AUDIO_SIZE_BYTES // (1024 * 1024)
            raise VoiceSTTError(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Audio file exceeds maximum allowed size ({max_mb} MB)."
            )

        # 2. Check Gnani Configuration
        if not settings.is_gnani_stt_ready:
            logger.info("Gnani STT is not configured. Running in mock/demo transcription mode.")
            return self._mock_transcription(audio_bytes, size, language)

        # 3. Call Gnani Prisma v2.5 REST API
        stt_url = f"{settings.GNANI_API_BASE_URL.rstrip('/')}/stt/v3"
        headers = {
            "X-API-Key-ID": settings.GNANI_API_KEY,
            "Accept": "application/json",
        }

        form_data = {
            "model": settings.GNANI_STT_MODEL,
            "language": language,
        }

        files = {
            "audio_file": (filename or "audio.wav", io.BytesIO(audio_bytes), content_type or "audio/wav")
        }

        try:
            async with httpx.AsyncClient(timeout=settings.GNANI_STT_TIMEOUT) as client:
                response = await client.post(
                    stt_url,
                    headers=headers,
                    data=form_data,
                    files=files
                )

                if response.status_code == 200:
                    data = response.json()
                    transcript = data.get("transcript", "").strip()
                    confidence = data.get("confidence", 0.95)
                    detected_lang = data.get("detected_language_code", language)
                    model_used = data.get("model", settings.GNANI_STT_MODEL)
                    duration = data.get("processing_time")

                    return TranscribeResponse(
                        success=True,
                        transcript=transcript,
                        provider="gnani_prisma",
                        model=model_used,
                        language=language,
                        detected_language=detected_lang,
                        confidence=confidence,
                        is_mock=False,
                        duration_seconds=duration,
                        audio_size_bytes=size,
                        message="Speech successfully transcribed by Gnani Prisma v2.5."
                    )
                else:
                    error_msg = response.text
                    logger.error("Gnani STT API returned %d: %s", response.status_code, error_msg)
                    raise VoiceSTTError(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Gnani Prisma STT error ({response.status_code}): Service returned invalid response."
                    )

        except httpx.TimeoutException:
            logger.error("Gnani STT request timed out after %s seconds.", settings.GNANI_STT_TIMEOUT)
            raise VoiceSTTError(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Gnani Prisma speech recognition timed out after {settings.GNANI_STT_TIMEOUT}s."
            )
        except httpx.RequestError as e:
            logger.error("Gnani STT network connection failed: %s", e)
            raise VoiceSTTError(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unable to reach Gnani Prisma STT service: {str(e)}"
            )

    def _mock_transcription(self, audio_bytes: bytes, size: int, language: str) -> TranscribeResponse:
        """
        Deterministic mock transcription for testing and demo mode when API keys are not supplied.
        """
        # Inspect size or patterns to return a realistic Kirana command
        # Default representative Tanglish command
        transcript = "Innaiku 5 kilo rice stock add pannunga."

        return TranscribeResponse(
            success=True,
            transcript=transcript,
            provider="mock_prisma",
            model="mock-prisma-v2.5",
            language=language,
            detected_language="ta-IN",
            confidence=0.95,
            is_mock=True,
            duration_seconds=round(size / 32000.0, 2),  # Estimated duration
            audio_size_bytes=size,
            message="Transcribed in mock/demo mode (GNANI_API_KEY not configured)."
        )


gnani_stt_service = GnaniSTTService()
