import logging
import uuid
from pathlib import Path

from app.services.rag import get_vectorstore, index_document
from app.services.parser import parse_document
from app.services.classifier import classify_document

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DIR = BACKEND_DIR / "sample_docs"
ALLOWED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".txt"}

# Exposed via /health so you can tell when the knowledge base is ready.
indexing_status = {"state": "pending", "indexed": 0, "failed": 0}


def index_sample_docs() -> None:
    """Index the bundled sample docs if the vector store is empty.

    Blocking (OCR + embeddings); run it in a background thread so the API can start
    serving immediately. Hosts with ephemeral disks (e.g. free Hugging Face Spaces)
    re-run this on every restart.
    """
    indexing_status["state"] = "running"
    try:
        if get_vectorstore()._collection.count() > 0:
            indexing_status["state"] = "skipped (vector store not empty)"
            return
    except Exception:
        logger.exception("Could not read vector store count; attempting sample indexing anyway")

    if not SAMPLE_DIR.exists():
        indexing_status["state"] = "skipped (no sample_docs)"
        return

    for file_path in sorted(SAMPLE_DIR.iterdir()):
        if file_path.suffix.lower() not in ALLOWED_EXTS or file_path.name.endswith("_preproc.png"):
            continue
        try:
            doc_id = str(uuid.uuid4())
            pages = parse_document(str(file_path), doc_id)
            classification = classify_document(pages, file_path.name)
            index_document(doc_id, pages, file_path.name, classification)
            indexing_status["indexed"] += 1
            logger.info("[startup] Indexed sample: %s", file_path.name)
        except Exception:
            indexing_status["failed"] += 1
            logger.exception("[startup] Failed to index %s", file_path.name)

    indexing_status["state"] = "done"
