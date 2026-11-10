"""Phase 6: Gnani Prisma v2.5 STT & Gnani Timbre v2.5 TTS Integration Tests."""
import io
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
import httpx

from backend.app.config import settings
from backend.app.schemas.voice import (
    TranscribeResponse,
    VoiceCommandResponse,
    VoiceStatusResponse,
    SpeakRequest,
)
from backend.app.schemas.ai import (
    CommandIntent,
    IntentCategory,
    CommandEntities,
)
from backend.app.services.gnani_stt_service import (
    GnaniSTTService,
    VoiceSTTError,
    gnani_stt_service,
)
from backend.app.services.gnani_tts_service import (
    GnaniTTSService,
    VoiceTTSError,
    gnani_tts_service,
)
from backend.app.models.product import Product


# =============================================================================
# 1. Voice Status Endpoint Tests
# =============================================================================

def test_voice_status_endpoint(client):
    """GET /api/voice/status returns 200 and schema with service status."""
    res = client.get("/api/voice/status")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "stt_ready" in data
    assert "tts_ready" in data
    assert data["stt_model"] == settings.GNANI_STT_MODEL
    assert data["tts_model"] == settings.GNANI_TTS_MODEL
    assert "Gnani" in data["provider"]


# =============================================================================
# 2. Gnani STT Unit & Validation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_stt_empty_audio_raises_error():
    """Empty audio payload raises VoiceSTTError 400."""
    service = GnaniSTTService()
    with pytest.raises(VoiceSTTError) as exc_info:
        await service.transcribe_audio(b"")
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Empty" in exc_info.value.message


@pytest.mark.asyncio
async def test_stt_oversized_audio_raises_error():
    """Audio exceeding max bytes raises VoiceSTTError 413."""
    service = GnaniSTTService()
    # Mock settings.MAX_AUDIO_SIZE_BYTES to 100 bytes for test
    oversized = b"x" * 200
    with patch.object(settings, "MAX_AUDIO_SIZE_BYTES", 100):
        with pytest.raises(VoiceSTTError) as exc_info:
            await service.transcribe_audio(oversized)
        assert exc_info.value.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


@pytest.mark.asyncio
async def test_stt_unconfigured_fallback():
    """When GNANI_API_KEY is unset, STT returns clean fallback mock transcript."""
    service = GnaniSTTService()
    with patch.object(settings, "GNANI_API_KEY", ""):
        res = await service.transcribe_audio(b"fake_audio_bytes_minimum_length_required" * 10)
        assert res.success is True
        assert len(res.transcript) > 0
        assert res.is_mock is True
        assert res.model == "mock-prisma-v2.5"


@pytest.mark.asyncio
async def test_stt_live_call_success():
    """Live call with valid response from Gnani API."""
    service = GnaniSTTService()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "transcript": "5 கிலோ அரிசி சேர்க்கவும்",
        "confidence": 0.94,
        "language": "ta-IN",
        "duration": 2.5,
    }

    with patch.object(settings, "GNANI_API_KEY", "gnani_test_key_123"):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            res = await service.transcribe_audio(b"valid_wav_bytes_length" * 15, language="ta-IN")

            assert res.success is True
            assert res.transcript == "5 கிலோ அரிசி சேர்க்கவும்"
            assert res.confidence == 0.94
            assert res.is_mock is False


@pytest.mark.asyncio
async def test_stt_timeout_raises_504():
    """STT timeout raises VoiceSTTError 504 Gateway Timeout."""
    service = GnaniSTTService()
    with patch.object(settings, "GNANI_API_KEY", "gnani_test_key_123"):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Connection timed out")
            with pytest.raises(VoiceSTTError) as exc_info:
                await service.transcribe_audio(b"audio_bytes_length_ok" * 15)
            assert exc_info.value.status_code == status.HTTP_504_GATEWAY_TIMEOUT


@pytest.mark.asyncio
async def test_stt_provider_error_raises_502():
    """STT upstream 500 error raises VoiceSTTError 502 Bad Gateway."""
    service = GnaniSTTService()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal upstream failure"

    with patch.object(settings, "GNANI_API_KEY", "gnani_test_key_123"):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(VoiceSTTError) as exc_info:
                await service.transcribe_audio(b"audio_bytes_length_ok" * 15)
            assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY


# =============================================================================
# 3. Gnani TTS Unit & Validation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_tts_empty_text_raises_400():
    """Empty or whitespace text raises VoiceTTSError 400."""
    service = GnaniTTSService()
    with pytest.raises(VoiceTTSError) as exc_info:
        await service.synthesize_speech("   ")
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_tts_oversized_text_raises_400():
    """Text exceeding 1000 characters raises VoiceTTSError 400."""
    service = GnaniTTSService()
    with pytest.raises(VoiceTTSError) as exc_info:
        await service.synthesize_speech("அரிசி " * 300)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_tts_unconfigured_produces_valid_wav():
    """When GNANI_API_KEY is unset, TTS produces valid RIFF WAV audio."""
    service = GnaniTTSService()
    with patch.object(settings, "GNANI_API_KEY", ""):
        wav_bytes, media_type, provider = await service.synthesize_speech("வணக்கம்! கடைக்கு என்ன வேண்டும்?")
        assert len(wav_bytes) > 44
        assert wav_bytes[:4] == b"RIFF"
        assert wav_bytes[8:12] == b"WAVE"


@pytest.mark.asyncio
async def test_tts_live_call_success():
    """Live call with binary audio returned from Gnani Timbre API."""
    service = GnaniTTSService()
    fake_wav = b"RIFF" + (b"\x00" * 36) + b"data" + (b"\x00" * 100)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "audio/wav"}
    mock_response.content = fake_wav

    with patch.object(settings, "GNANI_API_KEY", "gnani_test_key_123"):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            res, media_type, provider = await service.synthesize_speech("வணக்கம்")
            assert res == fake_wav


@pytest.mark.asyncio
async def test_tts_timeout_raises_504():
    """TTS timeout raises VoiceTTSError 504 Gateway Timeout."""
    service = GnaniTTSService()
    with patch.object(settings, "GNANI_API_KEY", "gnani_test_key_123"):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("TTS Timed out")
            with pytest.raises(VoiceTTSError) as exc_info:
                await service.synthesize_speech("வணக்கம்")
            assert exc_info.value.status_code == status.HTTP_504_GATEWAY_TIMEOUT


# =============================================================================
# 4. End-to-End API Integration Tests
# =============================================================================

def test_api_transcribe_audio_endpoint(client):
    """POST /api/voice/transcribe transcribes uploaded audio."""
    mock_transcribe = TranscribeResponse(
        success=True,
        transcript="Innaiku 5 kilo rice stock add pannunga.",
        provider="mock_prisma",
        model="mock-prisma-v2.5",
        language="ta-IN",
        detected_language="ta-IN",
        confidence=0.96,
        is_mock=True,
        duration_seconds=1.0,
        audio_size_bytes=300,
        message="Transcribed successfully."
    )
    with patch("backend.app.services.gnani_stt_service.gnani_stt_service.transcribe_audio", AsyncMock(return_value=mock_transcribe)):
        fake_audio = io.BytesIO(b"RIFF" + (b"\x00" * 300))
        files = {"audio_file": ("test.wav", fake_audio, "audio/wav")}
        res = client.post("/api/voice/transcribe", files=files, data={"language": "ta-IN"})
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["success"] is True
        assert "transcript" in data


def test_api_speak_endpoint_returns_wav(client):
    """POST /api/voice/speak returns audio/wav stream."""
    fake_wav = b"RIFF" + (b"\x00" * 36) + b"data" + (b"\x00" * 100)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "audio/wav"}
    mock_response.content = fake_wav

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        payload = {
            "text": "வணக்கம்! உங்கள் சரக்கு விவரங்கள் சரிபார்க்கவும்.",
            "language": "ta-IN",
            "speed": 1.0
        }
        res = client.post("/api/voice/speak", json=payload)
        assert res.status_code == status.HTTP_200_OK
        assert res.headers["content-type"].startswith("audio/wav")
        assert res.content[:4] == b"RIFF"


def test_api_command_with_transcript_workflow(client, db):
    """POST /api/voice/command with transcript_text creates confirmation preview."""
    # Seed product
    prod = Product(
        name="Ponni Boiled Rice",
        name_ta="பொன்னி அரிசி",
        category="Rice & Grains",
        sku="TEST-RIC-001",
        quantity=20.0,
        unit="kg",
        purchase_price=45.0,
        selling_price=54.0,
        minimum_stock_level=5.0,
    )
    db.add(prod)
    db.commit()

    mocked_intent = CommandIntent(
        intent=IntentCategory.ADD_STOCK,
        language="Tanglish",
        original_text="Innaiku 5 kilo rice stock add pannunga",
        normalized_text="Add 5 kg rice to inventory",
        entities=CommandEntities(product_name="rice", quantity=5.0, unit="kg"),
        confidence=0.98,
        requires_clarification=False
    )

    form_data = {
        "transcript_text": "Innaiku 5 kilo rice stock add pannunga",
        "language": "ta-IN"
    }

    with patch.object(settings, "GEMINI_API_KEY", "mock_key_xyz"), patch.object(settings, "GEMINI_ENABLED", True):
        with patch("backend.app.services.gemini_client.gemini_client.generate_intent_async", AsyncMock(return_value=mocked_intent)):
            res = client.post("/api/voice/command", data=form_data)
            assert res.status_code == status.HTTP_200_OK
            data = res.json()
            assert data["success"] is True
            assert data["requires_confirmation"] is True
            assert data["confirmation_preview"] is not None
            assert data["confirmation_preview"]["action"] == "ADD_STOCK"
            assert data["confirmation_preview"]["quantity"] == 5.0


def test_api_command_with_audio_file(client, db):
    """POST /api/voice/command with audio file executes end-to-end pipeline."""
    # Seed product
    prod = Product(
        name="Ponni Boiled Rice",
        name_ta="பொன்னி அரிசி",
        category="Rice & Grains",
        sku="TEST-RIC-002",
        quantity=10.0,
        unit="kg",
        purchase_price=45.0,
        selling_price=54.0,
        minimum_stock_level=5.0,
    )
    db.add(prod)
    db.commit()

    mocked_intent = CommandIntent(
        intent=IntentCategory.ADD_STOCK,
        language="Tanglish",
        original_text="Innaiku 5 kilo rice stock add pannunga",
        normalized_text="Add 5 kg rice to inventory",
        entities=CommandEntities(product_name="rice", quantity=5.0, unit="kg"),
        confidence=0.96,
        requires_clarification=False
    )

    fake_audio = io.BytesIO(b"fake_mic_recording_bytes_12345" * 15)
    files = {"audio_file": ("recording.webm", fake_audio, "audio/webm")}

    mock_transcribe = TranscribeResponse(
        success=True,
        transcript="Innaiku 5 kilo rice stock add pannunga",
        provider="mock_prisma",
        model="mock-prisma-v2.5",
        language="ta-IN",
        detected_language="ta-IN",
        confidence=0.96,
        is_mock=True,
        duration_seconds=1.0,
        audio_size_bytes=300,
        message="Transcribed successfully."
    )
    with patch.object(settings, "GEMINI_API_KEY", "mock_key_xyz"), patch.object(settings, "GEMINI_ENABLED", True):
        with patch("backend.app.services.gemini_client.gemini_client.generate_intent_async", AsyncMock(return_value=mocked_intent)):
            with patch("backend.app.services.gnani_stt_service.gnani_stt_service.transcribe_audio", AsyncMock(return_value=mock_transcribe)):
                res = client.post("/api/voice/command", files=files, data={"language": "ta-IN"})
                assert res.status_code == status.HTTP_200_OK
                data = res.json()
                assert data["success"] is True
                assert "transcript" in data
                assert data["intent"] is not None


def test_legacy_voice_process_endpoint(client):
    """POST /api/voice/process backwards compatibility test."""
    payload = {"command_text": "Innaiku sales evlo?"}
    res = client.post("/api/voice/process", json=payload)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["success"] is True
    assert "response_ta" in data
