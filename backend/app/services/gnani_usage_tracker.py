"""Gnani API Usage Tracking and Local Credit Guard Service.

Audits every live STT and TTS request into the SQLite database.
Enforces a configurable testing budget (default: 1,000 credits) to prevent overconsumption.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.models.gnani_usage import GnaniApiUsage

logger = logging.getLogger(__name__)


class GnaniUsageTracker:
    """Thread-safe usage tracker with database persistence and credit guard."""

    @staticmethod
    def record_usage(
        service: str,
        provider: str = "gnani",
        success: bool = True,
        status_code: int = 200,
        duration_ms: float = 0.0,
        input_size: Optional[str] = None,
        provider_reported_credits: Optional[float] = None,
        estimated_credits: float = 1.0,
        error_category: Optional[str] = None,
        error_detail: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> GnaniApiUsage:
        """
        Record a single STT or TTS API transaction into SQLite.
        """
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            record = GnaniApiUsage(
                provider=provider,
                service=service.upper(),
                timestamp=datetime.now(timezone.utc),
                status_code=status_code,
                success=success,
                duration_ms=round(duration_ms, 2),
                input_size=input_size,
                provider_reported_credits=provider_reported_credits,
                estimated_credits=round(estimated_credits, 2),
                error_category=error_category,
                error_detail=error_detail[:500] if error_detail else None,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record
        except Exception as e:
            logger.warning("Failed to record Gnani API usage: %s", e)
            db.rollback()
        finally:
            if close_db:
                db.close()

    @staticmethod
    def is_budget_exceeded(db: Optional[Session] = None) -> bool:
        """
        Check if total estimated/reported credits exceed the local testing budget (1,000 credits).
        """
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            total_est = db.query(func.sum(GnaniApiUsage.estimated_credits)).scalar() or 0.0
            return total_est >= settings.GNANI_TEST_CREDIT_BUDGET
        except Exception as e:
            logger.warning("Error checking budget guard: %s", e)
            return False
        finally:
            if close_db:
                db.close()

    @staticmethod
    def get_summary(db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Return structured summary of Gnani API usage for dashboard and health reports.
        """
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            total_calls = db.query(func.count(GnaniApiUsage.id)).scalar() or 0
            stt_calls = db.query(func.count(GnaniApiUsage.id)).filter(GnaniApiUsage.service == "STT").scalar() or 0
            tts_calls = db.query(func.count(GnaniApiUsage.id)).filter(GnaniApiUsage.service == "TTS").scalar() or 0
            success_calls = db.query(func.count(GnaniApiUsage.id)).filter(GnaniApiUsage.success == True).scalar() or 0
            failed_calls = db.query(func.count(GnaniApiUsage.id)).filter(GnaniApiUsage.success == False).scalar() or 0

            total_est_credits = db.query(func.sum(GnaniApiUsage.estimated_credits)).scalar() or 0.0
            total_provider_credits = db.query(func.sum(GnaniApiUsage.provider_reported_credits)).scalar()

            recent_records = (
                db.query(GnaniApiUsage)
                .order_by(GnaniApiUsage.id.desc())
                .limit(20)
                .all()
            )

            recent_list = [
                {
                    "id": r.id,
                    "provider": r.provider,
                    "service": r.service,
                    "timestamp": r.timestamp.isoformat(),
                    "status_code": r.status_code,
                    "success": r.success,
                    "duration_ms": r.duration_ms,
                    "input_size": r.input_size,
                    "provider_reported_credits": r.provider_reported_credits,
                    "estimated_credits": r.estimated_credits,
                    "error_category": r.error_category,
                }
                for r in recent_records
            ]

            budget_limit = settings.GNANI_TEST_CREDIT_BUDGET
            remaining_budget = max(0.0, budget_limit - total_est_credits)

            return {
                "total_calls": total_calls,
                "stt_calls": stt_calls,
                "tts_calls": tts_calls,
                "successful_calls": success_calls,
                "failed_calls": failed_calls,
                "testing_budget_limit": budget_limit,
                "estimated_credits_used": round(total_est_credits, 2),
                "estimated_credits_remaining": round(remaining_budget, 2),
                "provider_confirmed_credits": total_provider_credits,
                "provider_confirmed_available": total_provider_credits is not None,
                "budget_guard_active": True,
                "budget_exceeded": total_est_credits >= budget_limit,
                "recent_history": recent_list,
            }
        except Exception as e:
            logger.error("Error generating usage summary: %s", e)
            return {
                "total_calls": 0,
                "error": str(e),
                "testing_budget_limit": settings.GNANI_TEST_CREDIT_BUDGET
            }
        finally:
            if close_db:
                db.close()


usage_tracker = GnaniUsageTracker()

