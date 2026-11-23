"""Single entry point for every LLM call in the backend.

Routing policy:
  1. Groq is tried first, up to GROQ_MAX_ATTEMPTS times (default 3) with exponential backoff.
     Errors that cannot succeed on retry (bad request, auth, unknown/decommissioned model)
     stop the Groq attempts early instead of burning the remaining retries.
  2. If Groq is not configured or every attempt failed, Gemini is used as the fallback,
     up to GEMINI_MAX_ATTEMPTS times.
  3. If both providers fail, LLMUnavailableError is raised; callers degrade gracefully.

Prompt and document content is never logged: uploads may contain sensitive data.
"""

from __future__ import annotations

import base64
import logging
import time
from functools import lru_cache
from typing import Callable

from app.core.config import get_settings

logger = logging.getLogger(__name__)

GROQ_BACKOFF_SECONDS = 1.0  # sleeps 1s, 2s, 4s ... between Groq attempts


class LLMUnavailableError(RuntimeError):
    """Raised when neither Groq nor Gemini produced a usable response."""


class EmptyResponseError(RuntimeError):
    """The provider answered but returned no text."""


# ---------------------------------------------------------------------------
# Clients (created lazily so a missing optional key never breaks startup)
# ---------------------------------------------------------------------------

@lru_cache
def _groq_client():
    from groq import Groq

    settings = get_settings()
    # max_retries=0: the retry policy lives here, not hidden inside the SDK.
    return Groq(
        api_key=settings.groq_api_key,
        max_retries=0,
        timeout=settings.llm_timeout_seconds,
    )


@lru_cache
def _gemini_client():
    from google import genai
    from google.genai import types

    settings = get_settings()
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=settings.llm_timeout_seconds * 1000),
    )


# ---------------------------------------------------------------------------
# Provider-specific calls
# ---------------------------------------------------------------------------

def _groq_chat(model: str, messages: list[dict], json_mode: bool, max_tokens: int | None) -> str:
    kwargs: dict = {"model": model, "messages": messages, "temperature": 0}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if max_tokens:
        kwargs["max_completion_tokens"] = max_tokens
    if model.startswith("openai/gpt-oss"):
        # Reasoning model: keep it fast and keep the reasoning out of the answer.
        kwargs["reasoning_effort"] = "low"
        kwargs["include_reasoning"] = False

    completion = _groq_client().chat.completions.create(**kwargs)
    text = (completion.choices[0].message.content or "").strip()
    if not text:
        raise EmptyResponseError("Groq returned an empty response")
    return text


def _gemini_generate(contents, system: str | None, json_mode: bool) -> str:
    from google.genai import types

    settings = get_settings()
    # No temperature / max_output_tokens: current Gemini models ignore custom sampling
    # params, and thinking tokens count against max_output_tokens (truncating answers).
    config = types.GenerateContentConfig(
        system_instruction=system or None,
        response_mime_type="application/json" if json_mode else None,
    )
    response = _gemini_client().models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=config,
    )
    text = (response.text or "").strip()
    if not text:
        raise EmptyResponseError("Gemini returned an empty response")
    return text


def _is_permanent_groq_error(exc: Exception) -> bool:
    try:
        import groq
    except ImportError:  # pragma: no cover
        return False
    return isinstance(
        exc,
        (
            groq.BadRequestError,
            groq.AuthenticationError,
            groq.PermissionDeniedError,
            groq.NotFoundError,
            groq.UnprocessableEntityError,
        ),
    )


def _is_permanent_gemini_error(exc: Exception) -> bool:
    try:
        from google.genai import errors
    except ImportError:  # pragma: no cover
        return False
    # 4xx other than 408/429 will not succeed on retry.
    return isinstance(exc, errors.ClientError) and getattr(exc, "code", None) not in (408, 429)


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _route(
    purpose: str,
    groq_call: Callable[[], str] | None,
    gemini_call: Callable[[], str] | None,
) -> str:
    settings = get_settings()
    errors: list[str] = []

    if groq_call is not None:
        for attempt in range(1, settings.groq_max_attempts + 1):
            try:
                start = time.perf_counter()
                text = groq_call()
                logger.info(
                    "LLM ok purpose=%s provider=groq attempt=%s elapsed_ms=%.0f",
                    purpose, attempt, (time.perf_counter() - start) * 1000,
                )
                return text
            except Exception as exc:  # noqa: BLE001 - any failure triggers retry/fallback
                errors.append(f"groq#{attempt}: {type(exc).__name__}: {exc}")
                permanent = _is_permanent_groq_error(exc)
                logger.warning(
                    "LLM fail purpose=%s provider=groq attempt=%s/%s permanent=%s error=%s: %s",
                    purpose, attempt, settings.groq_max_attempts, permanent, type(exc).__name__, exc,
                )
                if permanent:
                    break
                if attempt < settings.groq_max_attempts:
                    time.sleep(GROQ_BACKOFF_SECONDS * (2 ** (attempt - 1)))

    if gemini_call is not None:
        if groq_call is not None:
            logger.warning("LLM fallback purpose=%s groq->gemini", purpose)
        for attempt in range(1, settings.gemini_max_attempts + 1):
            try:
                start = time.perf_counter()
                text = gemini_call()
                logger.info(
                    "LLM ok purpose=%s provider=gemini attempt=%s elapsed_ms=%.0f",
                    purpose, attempt, (time.perf_counter() - start) * 1000,
                )
                return text
            except Exception as exc:  # noqa: BLE001
                errors.append(f"gemini#{attempt}: {type(exc).__name__}: {exc}")
                logger.warning(
                    "LLM fail purpose=%s provider=gemini attempt=%s/%s error=%s: %s",
                    purpose, attempt, settings.gemini_max_attempts, type(exc).__name__, exc,
                )
                if _is_permanent_gemini_error(exc):
                    break
                if attempt < settings.gemini_max_attempts:
                    time.sleep(2 ** (attempt - 1))

    raise LLMUnavailableError(f"All LLM providers failed for '{purpose}': " + " | ".join(errors or ["no provider configured"]))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def complete(
    purpose: str,
    prompt: str,
    *,
    system: str | None = None,
    json_mode: bool = False,
    max_tokens: int | None = None,
) -> str:
    """Text completion. Returns the model's answer text."""
    settings = get_settings()

    groq_call = None
    if settings.groq_api_key and settings.groq_text_model:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        groq_call = lambda: _groq_chat(settings.groq_text_model, messages, json_mode, max_tokens)  # noqa: E731

    gemini_call = None
    if settings.gemini_api_key:
        gemini_call = lambda: _gemini_generate(prompt, system, json_mode)  # noqa: E731

    return _route(purpose, groq_call, gemini_call)


def complete_with_image(
    purpose: str,
    prompt: str,
    image_bytes: bytes,
    *,
    mime_type: str = "image/jpeg",
    max_tokens: int | None = None,
) -> str:
    """Vision completion over a single image. Groq is skipped if GROQ_VISION_MODEL is empty."""
    settings = get_settings()

    groq_call = None
    if settings.groq_api_key and settings.groq_vision_model:
        data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }]
        groq_call = lambda: _groq_chat(settings.groq_vision_model, messages, False, max_tokens)  # noqa: E731

    gemini_call = None
    if settings.gemini_api_key:
        def gemini_call() -> str:
            from google.genai import types

            return _gemini_generate(
                [types.Part.from_bytes(data=image_bytes, mime_type=mime_type), prompt],
                None,
                False,
            )

    return _route(purpose, groq_call, gemini_call)


def provider_summary() -> dict:
    """Non-secret description of the active LLM configuration (for logs/health)."""
    s = get_settings()
    return {
        "primary": {"provider": "groq", "enabled": bool(s.groq_api_key), "text_model": s.groq_text_model,
                    "vision_model": s.groq_vision_model or None, "max_attempts": s.groq_max_attempts},
        "fallback": {"provider": "gemini", "enabled": bool(s.gemini_api_key), "model": s.gemini_model,
                     "max_attempts": s.gemini_max_attempts},
    }
