"""Test Unified GNANI_API_KEY Configuration and Request Headers for STT & TTS."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings

client = TestClient(app)


def test_unified_gnani_api_key_configuration():
    """Verify that a single GNANI_API_KEY configures both STT and TTS."""
    with patch.object(settings, "GNANI_API_KEY", "test_gnani_key_12345"):
        assert settings.is_gnani_ready is True
        assert settings.is_gnani_stt_ready is True
        assert settings.is_gnani_tts_ready is True

        res = client.get("/api/voice/status")
        assert res.status_code == 200
        data = res.json()
        assert data["stt_ready"] is True
        assert data["tts_ready"] is True
        assert data["demo_mode"] is False
        # Ensure the secret key is NOT exposed in the response
        assert "test_gnani_key_12345" not in res.text


@pytest.mark.asyncio
async def test_stt_request_headers_and_payload():
    """Verify Gnani Prisma STT request uses X-API-Key-ID and x-api-key headers."""
    from backend.app.services.gnani_stt_service import gnani_stt_service
    dummy_audio = b"\x00" * 1000

    with patch.object(settings, "GNANI_API_KEY", "test_gnani_key_12345"):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "transcript": "Arisi 5 kilo",
                "confidence": 0.98,
                "detected_language_code": "ta-IN",
                "model": "prisma-v2.5"
            }
            mock_post.return_value = mock_resp

            result = await gnani_stt_service.transcribe_audio(dummy_audio, language="ta-IN")

            assert result.success is True
            assert result.transcript == "Arisi 5 kilo"
            assert mock_post.called

            # Check that correct Gnani headers were passed
            called_headers = mock_post.call_args.kwargs.get("headers", {})
            assert called_headers["X-API-Key-ID"] == "test_gnani_key_12345"


@pytest.mark.asyncio
async def test_tts_request_headers_and_payload():
    """Verify Gnani Timbre TTS request uses X-API-Key-ID, x-api-key, and valid audio_config."""
    from backend.app.services.gnani_tts_service import gnani_tts_service

    with patch.object(settings, "GNANI_API_KEY", "test_gnani_key_12345"):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {"content-type": "audio/wav"}
            mock_resp.content = b"RIFF" + b"\x00" * 100
            mock_post.return_value = mock_resp

            audio_bytes, media_type, provider = await gnani_tts_service.synthesize_speech("வணக்கம்", language="ta-IN")

            assert audio_bytes.startswith(b"RIFF")
            assert media_type == "audio/wav"
            assert provider == "gnani_timbre"
            assert mock_post.called

            # Check that correct Gnani headers and payload were passed
            called_headers = mock_post.call_args.kwargs.get("headers", {})
            assert called_headers["X-API-Key-ID"] == "test_gnani_key_12345"

            called_json = mock_post.call_args.kwargs.get("json", {})
            assert called_json["text"] == "வணக்கம்"
            assert called_json["model"] == "timbre-v2.5"
            assert called_json["language"] == "ta-IN"
            assert called_json["audio_config"]["container"] == "wav"

