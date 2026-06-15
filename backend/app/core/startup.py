import os
import uuid
from pathlib import Path
from app.services.rag import get_vectorstore, index_document
from app.services.parser import parse_document
from app.services.classifier import classify_document

BACKEND_DIR = Path(__file__).resolve().parents[2]
SAMPLE_DIR = BACKEND_DIR / "sample_docs"

async def index_sample_docs():
    """Index sample docs if vector store is empty."""
    try:
        count = get_vectorstore()._collection.count()
        if count > 0:
            return  # Already indexed
    except Exception:
        pass

    if not SAMPLE_DIR.exists():
        return

    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".txt"}
    for file_path in SAMPLE_DIR.iterdir():
        if file_path.suffix.lower() not in allowed_exts:
            continue
        try:
            doc_id = str(uuid.uuid4())
            pages = parse_document(str(file_path), doc_id)
            classification = classify_document(pages, file_path.name)
            index_document(doc_id, pages, file_path.name, classification)
            print(f"[startup] Indexed sample: {file_path.name}")
        except Exception as e:
            print(f"[startup] Failed to index {file_path.name}: {e}")
