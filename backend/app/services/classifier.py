import json
import os
from groq import Groq

from app.core.config import get_settings

settings = get_settings()

# Initialize Groq client
client = Groq(api_key=settings.groq_api_key)

CLASSIFICATION_SCHEMA = {
    "doc_type": "invoice | report | contract | form | letter | research | manual | other",
    "topics": ["list of relevant domain topics, e.g. finance, legal, medical, technical, HR"],
    "content_features": {
        "has_tables": "bool",
        "has_handwriting": "bool",
        "has_images": "bool",
        "is_scanned": "bool",
        "language": "ISO 639-1 code e.g. en, hi, fr",
        "page_count": "int",
    },
    "sensitivity_level": "public | internal | confidential | restricted",
    "sensitivity_reason": "one sentence explaining the sensitivity rating",
    "summary": "1-2 sentence plain-English summary of what this document contains",
}

SYSTEM_PROMPT = f"""You are a document classification expert.
Analyze the provided document text and metadata, then respond with ONLY a valid JSON object.
Do not include any explanation, preamble, or markdown fences — raw JSON only.
Use this exact schema:
{json.dumps(CLASSIFICATION_SCHEMA, indent=2)}

For sensitivity_level:
- public: no sensitive info
- internal: business info, not for external sharing
- confidential: personal data, financial records, legal docs
- restricted: medical records, government IDs, passwords, credentials
"""


def _default_classification(pages: list, filename: str, reason: str = "Classification fallback applied.") -> dict:
    return {
        "doc_type": "other",
        "topics": [],
        "content_features": {
            "has_tables": any(p.get("tables") for p in pages),
            "has_handwriting": False,
            "has_images": any(p.get("image_path") for p in pages),
            "is_scanned": any(p.get("parse_mode") in ["ocr", "doctr"] for p in pages),
            "language": "en",
            "page_count": len(pages),
        },
        "sensitivity_level": "internal",
        "sensitivity_reason": reason,
        "summary": f"Document: {filename}",
    }


def _normalize_classification(raw: dict, pages: list, filename: str) -> dict:
    fallback = _default_classification(pages, filename)
    if not isinstance(raw, dict):
        return fallback

    features = raw.get("content_features")
    if not isinstance(features, dict):
        features = {}

    normalized = {
        "doc_type": raw.get("doc_type") or fallback["doc_type"],
        "topics": raw.get("topics") if isinstance(raw.get("topics"), list) else fallback["topics"],
        "content_features": {
            "has_tables": bool(features.get("has_tables", fallback["content_features"]["has_tables"])),
            "has_handwriting": bool(features.get("has_handwriting", fallback["content_features"]["has_handwriting"])),
            "has_images": bool(features.get("has_images", fallback["content_features"]["has_images"])),
            "is_scanned": bool(features.get("is_scanned", fallback["content_features"]["is_scanned"])),
            "language": features.get("language") or fallback["content_features"]["language"],
            "page_count": int(features.get("page_count") or fallback["content_features"]["page_count"]),
        },
        "sensitivity_level": raw.get("sensitivity_level") or fallback["sensitivity_level"],
        "sensitivity_reason": raw.get("sensitivity_reason") or fallback["sensitivity_reason"],
        "summary": raw.get("summary") or fallback["summary"],
    }
    return normalized


def classify_document(pages: list, filename: str) -> dict:
    """
    Takes parsed pages list and filename.
    Returns classification dict matching CLASSIFICATION_SCHEMA.
    """
    # Build a text sample — first 3 pages, max 3000 chars total
    sample_text = ""
    for page in pages[:3]:
        sample_text += f"\n--- Page {page['page_num']} ---\n{page['text'][:1000]}"
        for tbl in page.get("tables", []):
            sample_text += f"\n[TABLE] Headers: {tbl['headers']}"

    user_message = f"""Filename: {filename}
Total pages: {len(pages)}
Has tables: {any(p.get('tables') for p in pages)}
Parsed via OCR: {any(p.get('parse_mode') in ['ocr', 'doctr'] for p in pages)}

Document text sample:
{sample_text[:3000]}"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        
        raw = completion.choices[0].message.content
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        
        return _normalize_classification(json.loads(raw), pages, filename)
    except Exception as e:
        print(f"Classification error: {e}")
        return _default_classification(pages, filename, "Classification failed; defaulting to internal.")
