"""Gnani Prisma v2.5 Speech-to-Text (STT) Service.
Verified API integration with https://api.vachana.ai/stt/v3.
"""
import io
import time
import asyncio
import logging
from typing import Optional, Tuple
import httpx
from fastapi import HTTPException, status, UploadFile
from backend.app.config import settings
from backend.app.schemas.voice import TranscribeResponse
from backend.app.services.gnani_usage_tracker import usage_tracker

logger = logging.getLogger(__name__)


def normalize_indic_language(lang: Optional[str]) -> str:
    """Normalize any language variant into Gnani Prisma supported codes (ta-IN or en-IN)."""
    if not lang:
        return "ta-IN"
    l = lang.lower().strip()
    if l in ("ta", "tamil", "tanglish", "ta-in", "ta_in", "ta-tamil"):
        return "ta-IN"
    if l in ("en", "english", "en-in", "en_in", "en-english"):
        return "en-IN"
    return "ta-IN"


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

        norm_lang = normalize_indic_language(language)

        # 2. Check Gnani Configuration
        if not settings.is_gnani_stt_ready:
            return self._mock_transcription(audio_bytes, size, norm_lang)

        # 3. Call Gnani Prisma v2.5 REST API with unified GNANI_API_KEY
        # Check credit budget guard
        if usage_tracker.is_budget_exceeded():
            logger.warning(
                "Gnani STT request blocked by local credit guard: budget of %s credits reached.",
                settings.GNANI_TEST_CREDIT_BUDGET
            )
            raise VoiceSTTError(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Gnani API testing credit budget ({settings.GNANI_TEST_CREDIT_BUDGET} credits) reached. Live requests blocked to preserve credits."
            )

        stt_url = f"{settings.GNANI_API_BASE_URL.rstrip('/')}/stt/v3"
        headers = {
            "X-API-Key-ID": settings.GNANI_API_KEY,
            "Accept": "application/json",
        }

        form_data = {
            "language_code": norm_lang,
        }

        files = {
            "audio_file": (filename or "recording.wav", io.BytesIO(audio_bytes), "audio/wav")
        }

        start_time = time.time()
        response = None
        last_exception = None

        # Execute with 1 safe retry on transient 504/timeout
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=settings.GNANI_STT_TIMEOUT) as client:
                    response = await client.post(
                        stt_url,
                        headers=headers,
                        data=form_data,
                        files=files
                    )
                    if response.status_code == 200:
                        break
                    elif response.status_code in (502, 503, 504) and attempt == 0:
                        logger.warning("Gnani STT returned transient status %d on attempt 1, retrying once...", response.status_code)
                        await asyncio.sleep(0.5)
                        files["audio_file"] = (filename or "recording.wav", io.BytesIO(audio_bytes), "audio/wav")
                        continue
                    else:
                        break
            except (httpx.TimeoutException, httpx.RequestError) as ex:
                last_exception = ex
                if attempt == 0:
                    logger.warning("Gnani STT encountered %s on attempt 1, retrying once...", type(ex).__name__)
                    await asyncio.sleep(0.5)
                    files["audio_file"] = (filename or "recording.wav", io.BytesIO(audio_bytes), "audio/wav")
                    continue
                break

        elapsed_ms = (time.time() - start_time) * 1000

        if response is not None:
            if response.status_code == 200:
                data = response.json()
                transcript = ""
                if isinstance(data, dict):
                    transcript = (
                        data.get("transcript") or
                        data.get("text") or
                        (data.get("data", {}).get("transcript") if isinstance(data.get("data"), dict) else "") or
                        (data.get("result", [{}])[0].get("transcript") if isinstance(data.get("result"), list) and data.get("result") else "") or
                        ""
                    ).strip()
                confidence = data.get("confidence", 0.95) if isinstance(data, dict) else 0.95
                detected_lang = data.get("detected_language_code", norm_lang) if isinstance(data, dict) else norm_lang
                model_used = data.get("model", settings.GNANI_STT_MODEL) if isinstance(data, dict) else settings.GNANI_STT_MODEL
                duration = data.get("processing_time") if isinstance(data, dict) else None

                est_credits = max(1.0, round((duration or (size / 32000.0)) / 15.0, 2))
                usage_tracker.record_usage(
                    service="STT",
                    provider="gnani_prisma",
                    success=True,
                    status_code=response.status_code,
                    duration_ms=elapsed_ms,
                    input_size=f"{size} bytes ({round(size/1024, 1)} KB)",
                    estimated_credits=est_credits,
                )

                return TranscribeResponse(
                    success=True,
                    transcript=transcript,
                    provider="gnani_prisma",
                    model=model_used,
                    language=norm_lang,
                    detected_language=detected_lang,
                    confidence=confidence,
                    is_mock=False,
                    duration_seconds=duration,
                    audio_size_bytes=size,
                    message="Speech successfully transcribed by Gnani Prisma v2.5."
                )
            elif response.status_code == 504:
                logger.error("Gnani STT returned HTTP 504 Gateway Timeout from origin: %s", response.text[:200])
                usage_tracker.record_usage(
                    service="STT",
                    provider="gnani_prisma",
                    success=False,
                    status_code=504,
                    duration_ms=elapsed_ms,
                    input_size=f"{size} bytes",
                    estimated_credits=0.0,
                    error_category="GATEWAY_TIMEOUT",
                    error_detail=response.text[:500],
                )
                raise VoiceSTTError(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="Voice processing-ல் தற்காலிக பிரச்சனை ஏற்பட்டுள்ளது. மீண்டும் பேசவும்."
                )
            else:
                error_msg = response.text
                err_detail_str = error_msg
                try:
                    err_json = response.json()
                    if isinstance(err_json, dict) and "error" in err_json:
                        err_detail_str = err_json["error"].get("message", error_msg)
                except Exception:
                    pass

                logger.error("Gnani STT API returned status %d: %s", response.status_code, error_msg[:200])
                usage_tracker.record_usage(
                    service="STT",
                    provider="gnani_prisma",
                    success=False,
                    status_code=response.status_code,
                    duration_ms=elapsed_ms,
                    input_size=f"{size} bytes",
                    estimated_credits=0.0,
                    error_category=f"HTTP_{response.status_code}",
                    error_detail=error_msg[:500],
                )
                raise VoiceSTTError(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Gnani Prisma STT error ({response.status_code}): {err_detail_str}"
                )

        if isinstance(last_exception, httpx.TimeoutException):
            usage_tracker.record_usage(
                service="STT",
                provider="gnani_prisma",
                success=False,
                status_code=504,
                duration_ms=elapsed_ms,
                input_size=f"{size} bytes",
                estimated_credits=0.0,
                error_category="TIMEOUT",
                error_detail=f"Timed out after {settings.GNANI_STT_TIMEOUT}s",
            )
            logger.error("Gnani STT request timed out after %s seconds.", settings.GNANI_STT_TIMEOUT)
            raise VoiceSTTError(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Voice processing-ல் தற்காலிக பிரச்சனை ஏற்பட்டுள்ளது. மீண்டும் பேசவும்."
            )
        elif isinstance(last_exception, httpx.RequestError):
            usage_tracker.record_usage(
                service="STT",
                provider="gnani_prisma",
                success=False,
                status_code=502,
                duration_ms=elapsed_ms,
                input_size=f"{size} bytes",
                estimated_credits=0.0,
                error_category="NETWORK_ERROR",
                error_detail=str(last_exception)[:500],
            )
            logger.error("Gnani STT network connection failed: %s", last_exception)
            raise VoiceSTTError(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Voice processing-ல் தற்காலிக பிரச்சனை ஏற்பட்டுள்ளது. மீண்டும் பேசவும்."
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
