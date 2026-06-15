import logging
import time
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta"

genai.configure(api_key=settings.gemini_api_key)


def sdk_version() -> str:
    try:
        return version("google-generativeai")
    except PackageNotFoundError:
        return "unknown"


def get_gemini_model_name() -> str:
    return settings.gemini_model


def _payload_summary(payload: Any) -> dict:
    if isinstance(payload, str):
        return {"type": "text", "chars": len(payload)}
    if isinstance(payload, list):
        return {
            "type": "multipart",
            "parts": [
                "text" if isinstance(part, str) else part.__class__.__name__
                for part in payload
            ],
        }
    return {"type": payload.__class__.__name__}


def log_gemini_call(purpose: str, payload: Any) -> None:
    # Do not log raw document or prompt content; uploads may contain sensitive data.
    logger.info(
        "Gemini call purpose=%s model=%s endpoint=%s sdk_version=%s payload=%s",
        purpose,
        settings.gemini_model,
        GEMINI_ENDPOINT,
        sdk_version(),
        _payload_summary(payload),
    )


def generate_content(purpose: str, payload: Any, **kwargs):
    log_gemini_call(purpose, payload)
    model = genai.GenerativeModel(settings.gemini_model)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(payload, **kwargs)
            usage = getattr(response, "usage_metadata", None)
            logger.info("Gemini response purpose=%s usage=%s", purpose, usage)
            return response
        except ResourceExhausted:
            if attempt == max_retries - 1:
                raise
            logger.warning("Rate limited (429) on %s. Retrying in %ss...", purpose, 2 ** attempt)
            time.sleep(2 ** attempt)


def response_text(response: Any) -> str:
    """Extract text without using the SDK's fragile response.text quick accessor."""
    candidates = getattr(response, "candidates", None) or []
    parts_text: list[str] = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            text = getattr(part, "text", None)
            if text:
                parts_text.append(text)

    if parts_text:
        return "".join(parts_text).strip()

    # Last resort for older/alternate response shapes. This can raise; callers
    # should handle that as a provider response failure.
    return (getattr(response, "text", "") or "").strip()


def validate_gemini_model() -> None:
    if not settings.gemini_validate_on_startup:
        logger.warning("Gemini startup validation skipped by VALIDATE_GEMINI_ON_STARTUP=false")
        return

    logger.info(
        "Validating Gemini configuration model=%s endpoint=%s sdk_version=%s",
        settings.gemini_model,
        GEMINI_ENDPOINT,
        sdk_version(),
    )
    try:
        generate_content(
            "startup_health_check",
            "Say OK.",
            generation_config={"max_output_tokens": 16},
        )
    except Exception as exc:
        logger.warning(
            "Gemini startup validation failed (likely due to a 429 rate limit). "
            "Continuing startup, but AI features may be temporarily unavailable. "
            "Error: %s",
            exc
        )
