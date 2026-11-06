"""AI Intelligence Router: Natural Language Voice/Text Command Endpoints."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.schemas.ai import (
    InterpretRequest,
    InterpretResponse,
    ConfirmActionRequest,
    ConfirmActionResponse,
    CancelActionRequest,
    CancelActionResponse,
    AIStatusResponse,
)
from backend.app.services.ai_service import (
    interpret_user_command,
    confirm_pending_action,
    cancel_pending_action,
)

router = APIRouter(prefix="/ai", tags=["AI Natural Language Intelligence"])


@router.get("/status", response_model=AIStatusResponse)
def get_ai_status():
    """
    Check Gemini API configuration and readiness without exposing credentials.
    """
    return AIStatusResponse(
        configured=bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip()),
        enabled=settings.GEMINI_ENABLED,
        model=settings.GEMINI_MODEL,
        provider="Google Gemini",
        ready=settings.is_gemini_ready,
    )


@router.post("/interpret", response_model=InterpretResponse, status_code=status.HTTP_200_OK)
async def interpret_command(
    request: InterpretRequest,
    db: Session = Depends(get_db)
):
    """
    Parse a Tamil, Tanglish, or English shopkeeper command using Gemini.
    Validates intent with Pydantic, resolves catalog products, and creates
    a safe confirmation preview without modifying the database.
    """
    return await interpret_user_command(db=db, text=request.text)


@router.post("/confirm", response_model=ConfirmActionResponse, status_code=status.HTTP_200_OK)
def confirm_action(
    request: ConfirmActionRequest,
    db: Session = Depends(get_db)
):
    """
    Execute a previously validated pending inventory adjustment or sale.
    Atomically verifies current stock and executes the database transaction.
    """
    return confirm_pending_action(db=db, action_id=request.action_id)


@router.post("/cancel", response_model=CancelActionResponse, status_code=status.HTTP_200_OK)
def cancel_action(request: CancelActionRequest):
    """
    Cancel and discard a pending action token without altering the database.
    """
    return cancel_pending_action(action_id=request.action_id)
