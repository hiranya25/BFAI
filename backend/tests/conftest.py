"""Test environment: isolated data dirs and dummy credentials, set before app modules import."""
import os
import sys
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

_tmp = Path(tempfile.mkdtemp(prefix="docintel-tests-"))
os.environ.update({
    "GROQ_API_KEY": "test-groq-key",
    "GEMINI_API_KEY": "test-gemini-key",
    "API_SECRET_KEY": "test-api-secret",
    "ENCRYPTION_KEY": Fernet.generate_key().decode(),
    "UPLOAD_DIR": str(_tmp / "raw_docs"),
    "THUMBNAIL_DIR": str(_tmp / "thumbnails"),
    "CHROMA_DIR": str(_tmp / "chroma_db"),
})
# Run from any cwd; load_dotenv() must not override the values above.
os.chdir(_tmp)

SAMPLE_DIR = BACKEND_DIR / "sample_docs"
