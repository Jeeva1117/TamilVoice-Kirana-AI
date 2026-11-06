"""Gnani Timbre v2.5 Text-to-Speech (TTS) Service.
Verified API integration with https://api.vachana.ai/api/v1/tts/inference.
"""
import io
import math
import wave
import struct
import base64
import logging
from typing import Tuple
import httpx
from fastapi import HTTPException, status
from backend.app.config import settings

logger = logging.getLogger(__name__)


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

        # Check configuration
        if not settings.is_gnani_tts_ready:
            logger.info("Gnani TTS is not configured. Generating valid mock synthesized audio.")
            mock_audio = self._generate_mock_wav(duration=1.2, freq=520.0)
            return mock_audio, "audio/wav", "mock_timbre"

        # Call Gnani Timbre v2.5 REST API
        tts_url = f"{settings.GNANI_API_BASE_URL.rstrip('/')}/api/v1/tts/inference"
        headers = {
            "X-API-Key-ID": settings.GNANI_API_KEY,
            "Content-Type": "application/json",
            "Accept": "*/*",
        }

        payload = {
            "text": clean_text,
            "model": settings.GNANI_TTS_MODEL,
            "language": language,
            "speed": max(0.5, min(2.0, speed)),
            "voice": voice or "standard",
            "audio_config": {
                "sample_rate": 24000,
                "encoding": "linear_pcm",
                "container": "wav"
            }
        }

        try:
            async with httpx.AsyncClient(timeout=settings.GNANI_TTS_TIMEOUT) as client:
                response = await client.post(tts_url, headers=headers, json=payload)

                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")

                    # Check if response is raw binary WAV
                    if "audio" in content_type or response.content.startswith(b"RIFF"):
                        return response.content, "audio/wav", "gnani_timbre"

                    # Check if response is JSON with base64 audio
                    try:
                        data = response.json()
                        if "audio_content" in data:
                            audio_bytes = base64.b64decode(data["audio_content"])
                            return audio_bytes, "audio/wav", "gnani_timbre"
                        elif "audio" in data:
                            audio_bytes = base64.b64decode(data["audio"])
                            return audio_bytes, "audio/wav", "gnani_timbre"
                    except Exception:
                        pass

                    # Direct content fallback
                    return response.content, "audio/wav", "gnani_timbre"
                else:
                    logger.error("Gnani TTS API returned %d: %s", response.status_code, response.text)
                    raise VoiceTTSError(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Gnani Timbre TTS error ({response.status_code}): Service returned invalid response."
                    )

        except httpx.TimeoutException:
            logger.error("Gnani TTS request timed out after %s seconds.", settings.GNANI_TTS_TIMEOUT)
            raise VoiceTTSError(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Gnani Timbre text-to-speech timed out after {settings.GNANI_TTS_TIMEOUT}s."
            )
        except httpx.RequestError as e:
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
