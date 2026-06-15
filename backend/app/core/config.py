import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

PLACEHOLDER_VALUES = {
    "",
    "replace-with-your-groq-api-key",
    "replace-with-a-long-random-api-secret",
    "replace-with-a-fernet-key",
    "your-random-32-char-string-here",
    "your-random-encryption-key-here",
}


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value in PLACEHOLDER_VALUES:
        raise RuntimeError(
            f"Missing required environment variable {name}. "
            "Create backend/.env from backend/.env.example before starting the API."
        )
    return value


def _first_required(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value and value not in PLACEHOLDER_VALUES:
            return value
    joined = " or ".join(names)
    raise RuntimeError(
        f"Missing required environment variable {joined}. "
        "Create backend/.env from backend/.env.example before starting the API."
    )


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


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    api_secret_key: str
    encryption_key: str
    upload_dir: Path
    thumbnail_dir: Path
    chroma_dir: str
    max_upload_mb: int
    allowed_origins: list[str]


@lru_cache
def get_settings() -> Settings:
    return Settings(
        groq_api_key=_required("GROQ_API_KEY"),
        api_secret_key=_required("API_SECRET_KEY"),
        encryption_key=_fernet_key("ENCRYPTION_KEY"),
        upload_dir=Path(os.getenv("UPLOAD_DIR", "./data/raw_docs")),
        thumbnail_dir=Path(os.getenv("THUMBNAIL_DIR", "./data/thumbnails")),
        chroma_dir=os.getenv("CHROMA_DIR", "./data/chroma_db"),
        max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "20")),
        allowed_origins=[
            origin.strip()
            for origin in os.getenv(
                "ALLOWED_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if origin.strip()
        ],
    )
