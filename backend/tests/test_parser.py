from app.services.parser import parse_document
from pathlib import Path

def test_parse_text():
    file_path = Path("sample_docs/support_notes.txt")
    if not file_path.exists():
        return
    pages = parse_document(str(file_path), "doc_txt")
    assert len(pages) == 1
    assert pages[0]["page_num"] == 1
    assert "text" in pages[0]["parse_mode"]
    assert "image_path" in pages[0]
    assert len(pages[0]["text"]) > 0

def test_parse_image():
    file_path = Path("sample_docs/product_brief_image.png")
    if not file_path.exists():
        return
    pages = parse_document(str(file_path), "doc_img")
    assert len(pages) == 1
    assert "ocr" in pages[0]["parse_mode"]
    assert len(pages[0]["text"]) > 0

def test_parse_pdf():
    file_path = Path("sample_docs/q3_ai_adoption_report.pdf")
    if not file_path.exists():
        return
    pages = parse_document(str(file_path), "doc_pdf")
    assert len(pages) > 0
    assert "text" in pages[0]["parse_mode"] or "mixed" in pages[0]["parse_mode"]
