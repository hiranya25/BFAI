from unittest.mock import patch
from app.services.classifier import classify_document

@patch('app.services.classifier.generate_content')
def test_classifier_fallback(mock_generate):
    # Mock an API failure (e.g. timeout or malformed response)
    mock_generate.side_effect = Exception("Mocked API error")
    
    pages = [
        {"page_num": 1, "text": "Dummy text content", "parse_mode": "text"}
    ]
    
    res = classify_document(pages, "dummy.pdf")
    
    # Should use fallback values
    assert res["doc_type"] == "other"
    assert res["sensitivity_level"] == "internal"
    assert "Classification failed" in res["sensitivity_reason"]
