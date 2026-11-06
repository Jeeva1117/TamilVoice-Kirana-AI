"""Voice Service: Connects Gnani STT, Gemini AI Intent Extraction, and Confirmation Pipeline."""
import logging
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.schemas.voice import VoiceCommandResponse
from backend.app.services.gnani_stt_service import gnani_stt_service
from backend.app.services.ai_service import interpret_user_command

logger = logging.getLogger(__name__)


class VoicePipelineService:
    """End-to-end voice pipeline: Audio -> STT -> Gemini Intent -> Catalog Resolution -> Confirmation."""

    async def process_voice_command(
        self,
        db: Session,
        audio_bytes: Optional[bytes] = None,
        transcript_text: Optional[str] = None,
        filename: str = "recording.wav",
        content_type: str = "audio/wav",
        language: str = "ta-IN"
    ) -> VoiceCommandResponse:
        """
        Execute full voice command pipeline without bypassing confirmation.
        """
        stt_provider = "direct_transcript"
        final_transcript = ""

        # Step 1: Speech-to-Text if audio is provided
        if audio_bytes and len(audio_bytes) > 0:
            stt_res = await gnani_stt_service.transcribe_audio(
                audio_bytes=audio_bytes,
                filename=filename,
                content_type=content_type,
                language=language
            )
            final_transcript = stt_res.transcript
            stt_provider = stt_res.provider
        elif transcript_text and transcript_text.strip():
            final_transcript = transcript_text.strip()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either voice audio file or transcript text must be provided."
            )

        if not final_transcript:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No speech could be recognized from the audio recording."
            )

        # Step 2: Gemini Intent Extraction & Catalog Resolution (reusing Phase 5)
        ai_res = await interpret_user_command(db=db, text=final_transcript, allow_mock=True)

        return VoiceCommandResponse(
            success=ai_res.success,
            transcript=final_transcript,
            stt_provider=stt_provider,
            intent=ai_res.intent,
            resolved_product=ai_res.resolved_product,
            candidate_products=ai_res.candidate_products,
            requires_confirmation=ai_res.requires_confirmation,
            confirmation_preview=ai_res.confirmation_preview,
            query_result=ai_res.query_result,
            message=ai_res.message,
            message_ta=ai_res.message_ta,
            tts_available=True,
        )


voice_service = VoicePipelineService()
