import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

PLACEHOLDER_VALUES = {
    "",
    "your-groq-api-key",
    "your-gemini-api-key",
    "replace-with-your-groq-api-key",
    "replace-with-your-gemini-api-key",
    "replace-with-a-long-random-api-secret",
    "replace-with-a-fernet-key",
    "your-random-32-char-string-here",
    "your-random-encryption-key-here",
}

ENV_HINT = "Copy backend/.env.example to backend/.env (or set the variable in your host's secrets)."


def _optional(name: str) -> str:
    value = os.getenv(name, "").strip()
    return "" if value in PLACEHOLDER_VALUES else value


def _required(name: str) -> str:
    value = _optional(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable {name}. {ENV_HINT}")
    return value


def _fernet_key(name: str) -> str:
    value = _required(name)
    try:
        Fernet(value.encode())
    except Exception as exc:
        raise RuntimeError(
            f"{name} must be a valid Fernet key. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        ) from exc
    return value


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default


@dataclass(frozen=True)
class Settings:
    # LLM providers: Groq is primary, Gemini is the fallback. At least one key is required.
    groq_api_key: str
    gemini_api_key: str
    groq_text_model: str
    groq_vision_model: str  # empty string = skip Groq for image extraction
    gemini_model: str
    groq_max_attempts: int
    gemini_max_attempts: int
    llm_timeout_seconds: int

    api_secret_key: str
    encryption_key: str
    upload_dir: Path
    thumbnail_dir: Path
    chroma_dir: str
    max_upload_mb: int
    allowed_origins: list[str]


@lru_cache
def get_settings() -> Settings:
    groq_api_key = _optional("GROQ_API_KEY")
    gemini_api_key = _optional("GEMINI_API_KEY")
    if not groq_api_key and not gemini_api_key:
        raise RuntimeError(
            "Missing LLM credentials: set GROQ_API_KEY (primary) and/or GEMINI_API_KEY (fallback). "
            + ENV_HINT
        )

    return Settings(
        groq_api_key=groq_api_key,
        gemini_api_key=gemini_api_key,
        groq_text_model=os.getenv("GROQ_TEXT_MODEL", "openai/gpt-oss-20b").strip(),
        groq_vision_model=os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip(),
        groq_max_attempts=max(1, _int("GROQ_MAX_ATTEMPTS", 3)),
        gemini_max_attempts=max(1, _int("GEMINI_MAX_ATTEMPTS", 2)),
        llm_timeout_seconds=max(5, _int("LLM_TIMEOUT_SECONDS", 60)),
        api_secret_key=_required("API_SECRET_KEY"),
        encryption_key=_fernet_key("ENCRYPTION_KEY"),
        upload_dir=Path(os.getenv("UPLOAD_DIR", "./data/raw_docs")),
        thumbnail_dir=Path(os.getenv("THUMBNAIL_DIR", "./data/thumbnails")),
        chroma_dir=os.getenv("CHROMA_DIR", "./data/chroma_db"),
        max_upload_mb=_int("MAX_UPLOAD_MB", 20),
        allowed_origins=[
            origin.strip()
            for origin in os.getenv(
                "ALLOWED_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if origin.strip()
        ],
    )
