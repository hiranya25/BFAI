import magic  # python-magic for real MIME detection
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from fastapi import HTTPException, Header

from app.core.config import get_settings

settings = get_settings()
FERNET = Fernet(settings.encryption_key.encode())

ALLOWED_MIMES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "text/plain",
}

API_SECRET = settings.api_secret_key


def validate_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_SECRET:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


def validate_file(content: bytes, filename: str, max_mb: int) -> Optional[str]:
    """Returns error string or None if valid."""
    # Size check
    if len(content) > max_mb * 1024 * 1024:
        return f"File exceeds {max_mb}MB limit"

    # Real MIME check (not just extension)
    detected_mime = magic.from_buffer(content, mime=True)
    if detected_mime not in ALLOWED_MIMES:
        return f"File type not allowed: {detected_mime}"

    # Extension sanity check
    ext = Path(filename).suffix.lower()
    if ext not in {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".txt"}:
        return f"Extension not allowed: {ext}"

    return None


def save_file(content: bytes, doc_id: str, upload_dir: Path) -> Path:
    """Save file with UUID name. Encrypts at rest."""
    # Encrypt content
    encrypted = FERNET.encrypt(content)
    file_path = upload_dir / f"{doc_id}.enc"
    file_path.write_bytes(encrypted)
    return file_path


def load_file(doc_id: str, upload_dir: Path) -> bytes:
    """Decrypt and return file bytes."""
    file_path = upload_dir / f"{doc_id}.enc"
    encrypted = file_path.read_bytes()
    return FERNET.decrypt(encrypted)
