"""Gnani API Usage Tracking Model for Credit Safety and Audit."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from backend.app.database import Base


class GnaniApiUsage(Base):
    __tablename__ = "gnani_api_usage"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False, default="gnani")  # gnani_prisma, gnani_timbre
    service = Column(String(20), nullable=False)  # STT or TTS
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    status_code = Column(Integer, nullable=False, default=200)
    success = Column(Boolean, nullable=False, default=True)
    duration_ms = Column(Float, nullable=False, default=0.0)
    input_size = Column(String(100), nullable=True)  # audio bytes or text char count
    provider_reported_credits = Column(Float, nullable=True)  # Populated only if provider returns usage
    estimated_credits = Column(Float, nullable=False, default=1.0)  # Clearly labeled as local estimate
    error_category = Column(String(50), nullable=True)  # TIMEOUT, AUTH, HTTP_502, etc.
    error_detail = Column(Text, nullable=True)

