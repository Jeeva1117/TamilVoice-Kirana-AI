"""Application Configuration."""
import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "TamilVoice Kirana AI"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./kirana_ai.db")
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    ]
    TIMEZONE: str = "Asia/Kolkata"
    DEFAULT_CURRENCY: str = "INR"
    DEBUG: bool = True

    # Google Gemini API Settings (Phase 5)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_ENABLED: bool = os.getenv("GEMINI_ENABLED", "true").lower() in ("true", "1", "yes")
    GEMINI_TIMEOUT_SECONDS: float = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "15.0"))

    # Gnani.ai Prisma STT & Timbre TTS Settings (Phase 6)
    GNANI_API_KEY: str = os.getenv("GNANI_API_KEY", "")
    GNANI_STT_MODEL: str = os.getenv("GNANI_STT_MODEL", "prisma-v2.5")
    GNANI_TTS_MODEL: str = os.getenv("GNANI_TTS_MODEL", "timbre-v2.5")
    GNANI_STT_ENABLED: bool = os.getenv("GNANI_STT_ENABLED", "true").lower() in ("true", "1", "yes")
    GNANI_TTS_ENABLED: bool = os.getenv("GNANI_TTS_ENABLED", "true").lower() in ("true", "1", "yes")
    GNANI_API_BASE_URL: str = os.getenv("GNANI_API_BASE_URL", "https://api.vachana.ai")
    GNANI_STT_TIMEOUT: float = float(os.getenv("GNANI_STT_TIMEOUT", "30.0"))
    GNANI_TTS_TIMEOUT: float = float(os.getenv("GNANI_TTS_TIMEOUT", "30.0"))
    MAX_AUDIO_SIZE_BYTES: int = int(os.getenv("MAX_AUDIO_SIZE_BYTES", str(10 * 1024 * 1024)))  # 10 MB

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def is_gemini_ready(self) -> bool:
        """Check if Gemini API is enabled and has a valid key configured."""
        return self.GEMINI_ENABLED and bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())

    @property
    def is_gnani_stt_ready(self) -> bool:
        """Check if Gnani Prisma STT is enabled and configured."""
        return self.GNANI_STT_ENABLED and bool(self.GNANI_API_KEY and self.GNANI_API_KEY.strip())

    @property
    def is_gnani_tts_ready(self) -> bool:
        """Check if Gnani Timbre TTS is enabled and configured."""
        return self.GNANI_TTS_ENABLED and bool(self.GNANI_API_KEY and self.GNANI_API_KEY.strip())


settings = Settings()
