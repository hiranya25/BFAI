from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.parser import parse_document

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_docs"


def _sample(name):
    path = SAMPLE_DIR / name
    if not path.exists():
        pytest.skip(f"sample {name} not present")
    return path


def test_parse_digital_pdf_uses_pymupdf_without_llm():
    path = _sample("q3_ai_adoption_report.pdf")
    with patch("app.services.parser.complete_with_image") as vision:
        pages = parse_document(str(path), "doc_pdf")
    assert len(pages) > 0
    assert pages[0]["parse_mode"] == "smart"
    assert pages[0]["extraction_method"] == "pymupdf_digital"
    assert len(pages[0]["text"]) > 0
    assert pages[0]["image_path"].endswith("_page_1.jpg")
    vision.assert_not_called()


def test_parse_image_uses_vision_llm():
    path = _sample("product_brief_image.png")
    with patch("app.services.parser.complete_with_image", return_value="# Product brief\n| a | b |\n|---|---|") as vision:
        pages = parse_document(str(path), "doc_img")
    assert len(pages) == 1
    assert pages[0]["extraction_method"] == "vision_llm"
    assert "Product brief" in pages[0]["text"]
    vision.assert_called_once()


def test_parse_text_file():
    path = _sample("support_notes.txt")
    with patch("app.services.parser.complete_with_image", return_value=""):
        pages = parse_document(str(path), "doc_txt")
    assert len(pages) >= 1
    assert all(p["parse_mode"] != "error" for p in pages)
    assert any(p["text"].strip() for p in pages)
