"""Application Configuration."""
import os
from pathlib import Path
from typing import List, Optional, Union
from dotenv import load_dotenv, dotenv_values
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate workspace root and backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent

# Read .env files with backend/.env taking priority
_backend_env = dotenv_values(BACKEND_DIR / ".env")
_root_env = dotenv_values(ROOT_DIR / ".env")

# Capture existing process environment variables before loading .env files so cloud platform
# variables (Render, Supabase, Docker, system environment) always take highest priority
_process_env = dict(os.environ)

# Populate process environment (backend/.env takes precedence over root .env)
load_dotenv(ROOT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)

# Re-apply process environment variables so platform-level variables (e.g. Render DATABASE_URL) are never overwritten
os.environ.update(_process_env)


def _get_config_value(key: str, default: str = "") -> str:
    """Read configuration value prioritizing process environment, then backend/.env, then root .env."""
    val = os.getenv(key)
    if val is not None and str(val).strip():
        return str(val).strip()
    val = _backend_env.get(key)
    if val is not None and str(val).strip():
        return str(val).strip()
    val = _root_env.get(key)
    if val is not None and str(val).strip():
        return str(val).strip()
    return default


class Settings(BaseSettings):
    PROJECT_NAME: str = "TamilVoice Kirana AI"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    DATABASE_URL: str = _get_config_value("DATABASE_URL", "sqlite:///./kirana_ai.db")

    # Application & Environment Settings
    ENVIRONMENT: str = _get_config_value("ENVIRONMENT", _get_config_value("APP_ENV", "development"))
    APP_ENV: str = _get_config_value("APP_ENV", "development")
    APP_HOST: str = _get_config_value("APP_HOST", "0.0.0.0" if os.getenv("PORT") else "127.0.0.1")
    APP_PORT: int = int(_get_config_value("PORT", _get_config_value("APP_PORT", "8000")))
    SECRET_KEY: str = _get_config_value("SECRET_KEY", "replace_with_a_secure_random_secret_key")
    FRONTEND_URL: str = _get_config_value("FRONTEND_URL", "")

    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
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
    TIMEZONE: str = _get_config_value("TIMEZONE", "Asia/Kolkata")
    DEFAULT_CURRENCY: str = _get_config_value("DEFAULT_CURRENCY", "INR")
    DEBUG: bool = _get_config_value("DEBUG", "True").lower() in ("true", "1", "yes")

    # Google Gemini API Settings (Phase 5) - Preserved
    GEMINI_API_KEY: str = _get_config_value("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = _get_config_value("GEMINI_MODEL", "gemini-3-flash-preview")
    GEMINI_ENABLED: bool = _get_config_value("GEMINI_ENABLED", "true").lower() in ("true", "1", "yes")
    GEMINI_TIMEOUT_SECONDS: float = float(_get_config_value("GEMINI_TIMEOUT_SECONDS", "15.0"))

    # Unified Gnani.ai Platform Configuration (Prisma v2.5 STT & Timbre v2.5 TTS)
    # The single GNANI_API_KEY powers both STT and TTS without requiring separate keys
    GNANI_API_KEY: str = _get_config_value("GNANI_API_KEY", "")
    GNANI_ACCESS_TOKEN: str = _get_config_value("GNANI_ACCESS_TOKEN", "") or _get_config_value("GNANI_API_KEY", "")
    GNANI_LANG_CODE: str = _get_config_value("GNANI_LANG_CODE", "ta-IN")
    GNANI_STT_MODEL: str = _get_config_value("GNANI_STT_MODEL", "prisma-v2.5")
    GNANI_TTS_MODEL: str = _get_config_value("GNANI_TTS_MODEL", "timbre-v2.5")
    GNANI_TTS_VOICE: str = _get_config_value("GNANI_TTS_VOICE", "Nalini")
    GNANI_STT_ENABLED: bool = _get_config_value("GNANI_STT_ENABLED", "true").lower() in ("true", "1", "yes")
    GNANI_TTS_ENABLED: bool = _get_config_value("GNANI_TTS_ENABLED", "true").lower() in ("true", "1", "yes")
    GNANI_API_BASE_URL: str = _get_config_value("GNANI_API_BASE_URL", "https://api.vachana.ai")
    GNANI_STT_TIMEOUT: float = float(_get_config_value("GNANI_STT_TIMEOUT", "30.0"))
    GNANI_TTS_TIMEOUT: float = float(_get_config_value("GNANI_TTS_TIMEOUT", "30.0"))
    GNANI_TEST_CREDIT_BUDGET: int = int(_get_config_value("GNANI_TEST_CREDIT_BUDGET", "1000"))
    MAX_AUDIO_SIZE_BYTES: int = int(_get_config_value("MAX_AUDIO_SIZE_BYTES", str(10 * 1024 * 1024)))  # 10 MB

    model_config = SettingsConfigDict(
        env_file=[str(BACKEND_DIR / ".env"), str(ROOT_DIR / ".env"), ".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def is_gemini_ready(self) -> bool:
        """Check if Gemini API is enabled and has a valid key configured."""
        return self.GEMINI_ENABLED and bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())

    @property
    def is_gnani_ready(self) -> bool:
        """Check if the single unified GNANI_API_KEY is configured for both STT and TTS."""
        return bool(self.GNANI_API_KEY and self.GNANI_API_KEY.strip())

    @property
    def is_gnani_stt_ready(self) -> bool:
        """Check if Gnani Prisma STT is enabled and configured with GNANI_API_KEY."""
        return self.GNANI_STT_ENABLED and self.is_gnani_ready

    @property
    def is_gnani_tts_ready(self) -> bool:
        """Check if Gnani Timbre TTS is enabled and configured with GNANI_API_KEY."""
        return self.GNANI_TTS_ENABLED and self.is_gnani_ready

    @property
    def is_postgres(self) -> bool:
        """Check if active database engine is PostgreSQL (Supabase/Render)."""
        db = (self.DATABASE_URL or "").strip().lower()
        return db.startswith("postgres://") or db.startswith("postgresql://")

    @property
    def is_production(self) -> bool:
        """Check if environment is set to production."""
        env = (self.ENVIRONMENT or self.APP_ENV or "").strip().lower()
        return env in ("production", "prod") or self.is_postgres


settings = Settings()
