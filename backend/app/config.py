"""Application Configuration."""
import os
from pathlib import Path
from typing import List, Optional, Union
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate workspace root and backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent

# Explicitly load .env files into environment variables (root .env, then backend .env)
load_dotenv(ROOT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")


class Settings(BaseSettings):
    PROJECT_NAME: str = "TamilVoice Kirana AI"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./kirana_ai.db")

    # Application Settings from .env.example
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_HOST: str = os.getenv("APP_HOST", "127.0.0.1")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "replace_with_a_secure_random_secret_key")

    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            v_clean = v.strip()
            if v_clean.startswith("[") and v_clean.endswith("]"):
                import json
                try:
                    return json.loads(v_clean)
                except Exception:
                    pass
            return [i.strip() for i in v_clean.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")
    DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "INR")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    # Google Gemini API Settings (Phase 5)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_ENABLED: bool = os.getenv("GEMINI_ENABLED", "true").lower() in ("true", "1", "yes")
    GEMINI_TIMEOUT_SECONDS: float = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "15.0"))

    # Gnani.ai Prisma STT & Timbre TTS Settings (Phase 6)
    GNANI_API_KEY: str = os.getenv("GNANI_API_KEY", "")
    GNANI_ACCESS_TOKEN: str = os.getenv("GNANI_ACCESS_TOKEN", "")
    GNANI_LANG_CODE: str = os.getenv("GNANI_LANG_CODE", "ta-IN")
    GNANI_STT_MODEL: str = os.getenv("GNANI_STT_MODEL", "prisma-v2.5")
    GNANI_TTS_MODEL: str = os.getenv("GNANI_TTS_MODEL", "timbre-v2.5")
    GNANI_STT_ENABLED: bool = os.getenv("GNANI_STT_ENABLED", "true").lower() in ("true", "1", "yes")
    GNANI_TTS_ENABLED: bool = os.getenv("GNANI_TTS_ENABLED", "true").lower() in ("true", "1", "yes")
    GNANI_API_BASE_URL: str = os.getenv("GNANI_API_BASE_URL", "https://api.vachana.ai")
    GNANI_STT_TIMEOUT: float = float(os.getenv("GNANI_STT_TIMEOUT", "30.0"))
    GNANI_TTS_TIMEOUT: float = float(os.getenv("GNANI_TTS_TIMEOUT", "30.0"))
    MAX_AUDIO_SIZE_BYTES: int = int(os.getenv("MAX_AUDIO_SIZE_BYTES", str(10 * 1024 * 1024)))  # 10 MB

    model_config = SettingsConfigDict(
        env_file=[str(ROOT_DIR / ".env"), str(BACKEND_DIR / ".env"), ".env"],
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
