"""StoreSetting Database Model: Persistent Kirana store identity, tax, contact, and voice settings."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from backend.app.database import Base


class StoreSetting(Base):
    __tablename__ = "store_settings"

    id = Column(Integer, primary_key=True, index=True)
    shop_name = Column(String(150), nullable=False, default="TamilVoice Kirana Store")
    shop_name_ta = Column(String(150), nullable=True, default="கிரானா மளிகைக் கடை")
    owner_name = Column(String(100), nullable=False, default="Kirana Proprietor")
    phone = Column(String(30), nullable=False, default="+91 98765 43210")
    whatsapp_number = Column(String(30), nullable=True)
    address = Column(Text, nullable=True, default="Main Bazaar, Tamil Nadu")
    email = Column(String(100), nullable=True)
    gstin = Column(String(30), nullable=True)
    currency = Column(String(10), nullable=False, default="INR")
    currency_symbol = Column(String(10), nullable=False, default="₹")
    preferred_language = Column(String(10), nullable=False, default="ta")
    voice_preferred_language = Column(String(20), nullable=False, default="ta")
    speech_speed = Column(Float, nullable=False, default=1.0)
    auto_speak_responses = Column(Boolean, nullable=False, default=True)
    low_stock_threshold_default = Column(Float, nullable=False, default=5.0)
    receipt_footer = Column(Text, nullable=True, default="நன்றி! மீண்டும் வருக! / Thank you, visit again!")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

