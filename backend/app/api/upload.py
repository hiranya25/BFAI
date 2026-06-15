import os
import uuid
import asyncio
import logging
from time import perf_counter
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, Header
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.security import validate_api_key, validate_file, save_file
from app.core.config import get_settings
from app.services.parser import parse_document
from app.services.classifier import classify_document
from app.services.rag import index_document

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)
settings = get_settings()

UPLOAD_DIR = settings.upload_dir
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_MB = settings.max_upload_mb


async def process_single_file(filename: str, content: bytes, doc_id: str, upload_index: int):
    """Generator yielding SSE events for one file."""
    filename = filename or "unknown.pdf"

    def event(status: str, data: dict = None):
        import json
        payload = {
            "doc_id": doc_id,
            "filename": filename,
            "upload_index": upload_index,
            "status": status,
        }
        if data:
            payload.update(data)
        return f"data: {json.dumps(payload)}\n\n"

    try:
        start = perf_counter()
        logger.info("Upload file start filename=%s bytes=%s doc_id=%s", filename, len(content), doc_id)
        yield event("validating")

        # Security: validate before saving
        error = validate_file(content, filename, MAX_MB)
        if error:
            yield event("error", {"message": error})
            return

        yield event("saving")
        save_file(content, doc_id, UPLOAD_DIR)

        yield event("parsing")
        # The parser tools (camelot, pdfplumber) require an unencrypted file path on disk.
        # We write a temporary decrypted file, parse it, and then securely delete it.
        ext = Path(filename).suffix or ".pdf"
        tmp_path = UPLOAD_DIR / f"{doc_id}{ext}"
        tmp_path.write_bytes(content)
        try:
            pages = await asyncio.to_thread(parse_document, str(tmp_path), doc_id)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        yield event("classifying")
        classification = await asyncio.to_thread(classify_document, pages, filename)

        yield event("indexing")
        await asyncio.to_thread(index_document, doc_id, pages, filename, classification)

        yield event("indexed", {
            "doc_type": classification.get("doc_type"),
            "sensitivity": classification.get("sensitivity_level"),
            "summary": classification.get("summary"),
            "page_count": len(pages),
            "classification": classification,
        })
        logger.info(
            "Upload file end filename=%s pages=%s doc_id=%s elapsed_ms=%.1f",
            filename,
            len(pages),
            doc_id,
            (perf_counter() - start) * 1000,
        )

    except Exception:
        logger.exception("Failed to process uploaded file %s", filename)
        yield event("error", {"message": "Processing failed for this file. Check backend logs for details."})


@router.post("/upload")
@limiter.limit("10/minute")
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    api_key: str = Depends(validate_api_key),
):
    """
    Accepts multiple files. Returns SSE stream with per-file status events.
    """
    if len(files) > 10:
        raise HTTPException(400, "Maximum 10 files per upload")

    # Read files into memory to prevent FastAPI from closing them
    # when the endpoint function returns the StreamingResponse.
    start = perf_counter()
    logger.info("Upload request start file_count=%s", len(files))
    file_data = []
    for f in files:
        content = await f.read()
        file_data.append((f.filename, content))

    async def generate():
        for upload_index, (filename, content) in enumerate(file_data):
            doc_id = str(uuid.uuid4())
            async for chunk in process_single_file(filename, content, doc_id, upload_index):
                yield chunk
            await asyncio.sleep(0.05)  # Small gap between files

    response = StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
    logger.info("Upload request accepted file_count=%s read_elapsed_ms=%.1f", len(file_data), (perf_counter() - start) * 1000)
    return response


@router.get("/pages/{image_filename:path}")
async def get_page_image(
    image_filename: str,
    key: str | None = None,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """Serve page thumbnail. Auth required."""
    from fastapi.responses import FileResponse
    from app.core.security import API_SECRET

    if (x_api_key or key) != API_SECRET:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Security: prevent path traversal
    safe_name = Path(image_filename).name
    thumb_path = settings.thumbnail_dir / safe_name

    if not thumb_path.exists():
        raise HTTPException(404, "Page image not found")
    if not str(thumb_path.resolve()).startswith(str(thumb_path.parent.resolve())):
        raise HTTPException(403, "Forbidden")

    return FileResponse(str(thumb_path), media_type="image/jpeg")
