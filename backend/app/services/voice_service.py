"""Voice Service: Connects Gnani STT, Gemini AI Intent Extraction, and Confirmation Pipeline."""
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.schemas.voice import VoiceCommandResponse
from backend.app.schemas.ai import CommandIntent, IntentCategory, CommandEntities
from backend.app.services.gnani_stt_service import gnani_stt_service, normalize_indic_language, VoiceSTTError
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
        language: str = "ta-IN",
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> VoiceCommandResponse:
        """
        Execute full voice command pipeline without bypassing confirmation.
        """
        norm_lang = normalize_indic_language(language)
        stt_provider = "direct_transcript"
        final_transcript = ""
        stt_error_detail = None

        # Step 1: Speech-to-Text if audio is provided
        if audio_bytes and len(audio_bytes) > 0:
            try:
                stt_res = await gnani_stt_service.transcribe_audio(
                    audio_bytes=audio_bytes,
                    filename=filename,
                    content_type=content_type,
                    language=norm_lang
                )
                final_transcript = (stt_res.transcript or "").strip()
                stt_provider = stt_res.provider
            except (VoiceSTTError, Exception) as stt_err:
                logger.warning("Gnani STT encountered error (%s). Checking if browser transcript is available.", stt_err)
                stt_error_detail = str(getattr(stt_err, "detail", stt_err))
                # Fallback to browser transcript if captured
                if transcript_text and transcript_text.strip():
                    final_transcript = transcript_text.strip()
                    stt_provider = "browser_speech_fallback"
                else:
                    # Return graceful Tamil error without calling Gemini
                    retry_msg_ta = "Voice processing-ல் தற்காலிக பிரச்சனை ஏற்பட்டுள்ளது. மீண்டும் பேசவும்."
                    retry_msg_en = "Temporary voice processing issue. Please speak again."
                    return VoiceCommandResponse(
                        success=False,
                        transcript="",
                        stt_provider="gnani_prisma",
                        intent=CommandIntent(
                            intent=IntentCategory.UNKNOWN,
                            language="Tamil",
                            original_text="",
                            normalized_text="Voice processing error",
                            entities=CommandEntities(),
                            confidence=0.0,
                            requires_clarification=False,
                        ),
                        resolved_product=None,
                        requires_confirmation=False,
                        message=retry_msg_en,
                        message_ta=retry_msg_ta,
                        message_tanglish="Voice processing-la problem vandhurukku. Marubadiyum pesunga.",
                        detected_language="Tamil",
                        spoken_response=retry_msg_ta,
                        stage_error=f"[Stage 4: Gnani STT] {stt_error_detail}",
                        tts_available=True,
                        session_id=session_id,
                        context=context,
                    )
        elif transcript_text and transcript_text.strip():
            final_transcript = transcript_text.strip()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either voice audio file or transcript text must be provided."
            )

        if not final_transcript:
            retry_msg_ta = "மன்னிக்கவும், உங்கள் குரல் கேட்கவில்லை. மீண்டும் பேசவும்."
            retry_msg_en = "No speech detected in audio. Please speak again."
            return VoiceCommandResponse(
                success=False,
                transcript="",
                stt_provider=stt_provider,
                intent=CommandIntent(
                    intent=IntentCategory.UNKNOWN,
                    language="Tamil",
                    original_text="",
                    normalized_text="Silent audio recording",
                    entities=CommandEntities(),
                    confidence=0.0,
                    requires_clarification=False,
                ),
                resolved_product=None,
                requires_confirmation=False,
                message=retry_msg_en,
                message_ta=retry_msg_ta,
                message_tanglish="Kural ketkala. Marubadiyum pesunga.",
                detected_language="Tamil",
                spoken_response=retry_msg_ta,
                tts_available=True,
                session_id=session_id,
                context=context,
            )

        logger.info(
            "Voice Diagnostic [STT Complete]: Provider=%s | Lang=%s | Transcript='%s' | AudioBytes=%d",
            stt_provider, norm_lang, final_transcript, len(audio_bytes) if audio_bytes else 0
        )

        # Step 2: Gemini Intent Extraction & Catalog Resolution (Production: allow_mock=False)
        ai_res = await interpret_user_command(
            db=db,
            text=final_transcript,
            allow_mock=False,
            session_id=session_id,
            context=context
        )

        logger.info(
            "Voice Diagnostic [AI Intent Complete]: Intent=%s | Product=%s | Qty=%s | NeedsClarification=%s | ClarificationReason='%s' | NeedsConfirm=%s | ResponseMsgTa='%s'",
            ai_res.intent.intent.value if ai_res.intent else "NONE",
            ai_res.intent.entities.product_name if (ai_res.intent and ai_res.intent.entities) else None,
            ai_res.intent.entities.quantity if (ai_res.intent and ai_res.intent.entities) else None,
            ai_res.intent.requires_clarification if ai_res.intent else False,
            ai_res.intent.clarification_question if (ai_res.intent and ai_res.intent.requires_clarification) else "N/A",
            ai_res.requires_confirmation,
            ai_res.message_ta or ai_res.message
        )

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
            message_tanglish=getattr(ai_res, "message_tanglish", None),
            detected_language=getattr(ai_res, "detected_language", "Tamil"),
            spoken_response=getattr(ai_res, "spoken_response", None),
            tts_available=True,
            session_id=ai_res.session_id,
            context=ai_res.context,
        )


voice_service = VoicePipelineService()
