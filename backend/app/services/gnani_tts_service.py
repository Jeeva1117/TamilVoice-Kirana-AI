"""Gnani Timbre v2.5 Text-to-Speech (TTS) Service.
Verified API integration with https://api.vachana.ai/api/v1/tts/inference.
"""
import io
import math
import wave
import struct
import base64
import time
import logging
from typing import Tuple, Optional
import httpx
from fastapi import HTTPException, status
from backend.app.config import settings
from backend.app.services.gnani_usage_tracker import usage_tracker

logger = logging.getLogger(__name__)


def normalize_indic_language(lang: Optional[str]) -> str:
    """Normalize any language variant into Gnani Timbre supported codes (ta-IN or en-IN)."""
    if not lang:
        return "ta-IN"
    l = lang.lower().strip()
    if l in ("ta", "tamil", "tanglish", "ta-in", "ta_in", "ta-tamil"):
        return "ta-IN"
    if l in ("en", "english", "en-in", "en_in", "en-english"):
        return "en-IN"
    return "ta-IN"


class VoiceTTSError(HTTPException):
    """Voice Text-to-Speech Exception."""
    def __init__(self, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR, detail: str = ""):
        super().__init__(status_code=status_code, detail=detail)
        self.message = detail


class GnaniTTSService:
    """Service to synthesize Tamil and Indian English speech using Gnani Timbre v2.5."""

    async def synthesize_speech(
        self,
        text: str,
        language: str = "ta-IN",
        speed: float = 1.0,
        voice: str = "standard"
    ) -> Tuple[bytes, str, str]:
        """
        Synthesize text to speech audio.
        Returns: (audio_bytes, media_type, provider_name)
        """
        if not text or not text.strip():
            raise VoiceTTSError(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text to synthesize cannot be empty."
            )

        clean_text = text.strip()
        if len(clean_text) > 1000:
            raise VoiceTTSError(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text exceeds maximum limit of 1000 characters."
            )

        norm_lang = normalize_indic_language(language)

        # Check configuration
        if not settings.is_gnani_tts_ready:
            return self._generate_mock_wav(duration=1.0), "audio/wav", "mock_timbre"

        # Check credit budget guard
        if usage_tracker.is_budget_exceeded():
            logger.warning(
                "Gnani TTS request blocked by local credit guard: budget of %s credits reached.",
                settings.GNANI_TEST_CREDIT_BUDGET
            )
            raise VoiceTTSError(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Gnani API testing credit budget ({settings.GNANI_TEST_CREDIT_BUDGET} credits) reached. Live requests blocked to preserve credits."
            )

        # Call Gnani Timbre v2.5 REST API with unified GNANI_API_KEY
        tts_url = f"{settings.GNANI_API_BASE_URL.rstrip('/')}/api/v1/tts/inference"
        headers = {
            "X-API-Key-ID": settings.GNANI_API_KEY,
            "Content-Type": "application/json",
            "Accept": "*/*",
        }

        selected_voice = voice if (voice and voice.lower() != "standard") else getattr(settings, "GNANI_TTS_VOICE", "Nalini")
        payload = {
            "text": clean_text,
            "model": settings.GNANI_TTS_MODEL,
            "language": norm_lang,
            "speed": max(0.5, min(2.0, speed)),
            "voice": selected_voice,
            "audio_config": {
                "sample_rate": 24000,
                "encoding": "linear_pcm",
                "container": "wav",
                "num_channels": 1,
                "sample_width": 2
            }
        }

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=settings.GNANI_TTS_TIMEOUT) as client:
                response = await client.post(tts_url, headers=headers, json=payload)

                # Fallback to SSE endpoint if inference returns 404
                if response.status_code == 404:
                    fallback_url = f"{settings.GNANI_API_BASE_URL.rstrip('/')}/api/v1/tts/sse"
                    response = await client.post(fallback_url, headers=headers, json=payload)

                elapsed_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    est_credits = max(1.0, round(len(clean_text) / 100.0, 2))
                    usage_tracker.record_usage(
                        service="TTS",
                        provider="gnani_timbre",
                        success=True,
                        status_code=response.status_code,
                        duration_ms=elapsed_ms,
                        input_size=f"{len(clean_text)} chars",
                        estimated_credits=est_credits,
                    )

                    logger.info(
                        "Voice Diagnostic [TTS Synthesized]: Text='%s' | Lang=%s | AudioBytes=%d | DurationMs=%.1f",
                        clean_text[:60], norm_lang, len(response.content), elapsed_ms
                    )
                    content_type = response.headers.get("content-type", "")

                    # 1. Check if response is raw binary WAV
                    if "audio" in content_type or response.content.startswith(b"RIFF"):
                        return response.content, "audio/wav", "gnani_timbre"

                    # 2. Check if response is JSON with base64 audio
                    try:
                        data = response.json()
                        for key in ("audio_content", "audio", "data", "audio_base64"):
                            if key in data and data[key]:
                                audio_bytes = base64.b64decode(data[key])
                                return audio_bytes, "audio/wav", "gnani_timbre"
                    except Exception:
                        pass

                    # 3. Direct content fallback
                    return response.content, "audio/wav", "gnani_timbre"
                else:
                    error_msg = response.text
                    logger.error("Gnani TTS API returned status %d: %s", response.status_code, error_msg[:200])
                    usage_tracker.record_usage(
                        service="TTS",
                        provider="gnani_timbre",
                        success=False,
                        status_code=response.status_code,
                        duration_ms=elapsed_ms,
                        input_size=f"{len(clean_text)} chars",
                        estimated_credits=0.0,
                        error_category=f"HTTP_{response.status_code}",
                        error_detail=error_msg[:500],
                    )
                    raise VoiceTTSError(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Gnani Timbre TTS error ({response.status_code}): Service returned invalid response."
                    )

        except httpx.TimeoutException:
            elapsed_ms = (time.time() - start_time) * 1000
            usage_tracker.record_usage(
                service="TTS",
                provider="gnani_timbre",
                success=False,
                status_code=504,
                duration_ms=elapsed_ms,
                input_size=f"{len(clean_text)} chars",
                estimated_credits=0.0,
                error_category="TIMEOUT",
                error_detail=f"Timed out after {settings.GNANI_TTS_TIMEOUT}s",
            )
            logger.error("Gnani TTS request timed out after %s seconds.", settings.GNANI_TTS_TIMEOUT)
            raise VoiceTTSError(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Gnani Timbre text-to-speech timed out after {settings.GNANI_TTS_TIMEOUT}s."
            )
        except httpx.RequestError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            usage_tracker.record_usage(
                service="TTS",
                provider="gnani_timbre",
                success=False,
                status_code=502,
                duration_ms=elapsed_ms,
                input_size=f"{len(clean_text)} chars",
                estimated_credits=0.0,
                error_category="NETWORK_ERROR",
                error_detail=str(e)[:500],
            )
            logger.error("Gnani TTS network connection failed: %s", e)
            raise VoiceTTSError(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unable to reach Gnani Timbre TTS service: {str(e)}"
            )

    def _generate_mock_wav(self, duration: float = 1.0, freq: float = 480.0) -> bytes:
        """
        Generate a gentle, valid 16-bit PCM WAV notification tone for mock/demo testing.
        """
        sample_rate = 16000
        n_samples = int(sample_rate * duration)
        buf = io.BytesIO()

        with wave.open(buf, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            for i in range(n_samples):
                t = float(i) / sample_rate
                # Dual-harmonic soft chime
                envelope = math.sin(math.pi * i / n_samples)
                val = int(envelope * 7000.0 * (0.7 * math.sin(2.0 * math.pi * freq * t) + 0.3 * math.sin(4.0 * math.pi * freq * t)))
                val = max(-32767, min(32767, val))
                wav_file.writeframes(struct.pack('<h', val))

        return buf.getvalue()


gnani_tts_service = GnaniTTSService()
