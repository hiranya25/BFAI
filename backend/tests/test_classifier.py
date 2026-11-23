import json
from unittest.mock import patch

from app.services.classifier import classify_document

PAGES = [{"page_num": 1, "text": "Invoice #123 total $400", "tables": [], "parse_mode": "smart"}]


@patch("app.services.classifier.complete")
def test_classifier_fallback_when_llm_unavailable(mock_complete):
    mock_complete.side_effect = Exception("Mocked API error")

    res = classify_document(PAGES, "dummy.pdf")

    assert res["doc_type"] == "other"
    assert res["sensitivity_level"] == "internal"
    assert "Classification failed" in res["sensitivity_reason"]


@patch("app.services.classifier.complete")
def test_classifier_parses_json_and_uses_json_mode(mock_complete):
    mock_complete.return_value = "```json\n" + json.dumps({
        "doc_type": "invoice",
        "topics": ["finance"],
        "content_features": {"has_tables": False, "language": "en", "page_count": 1},
        "sensitivity_level": "confidential",
        "sensitivity_reason": "Financial record.",
        "summary": "An invoice.",
    }) + "\n```"

    res = classify_document(PAGES, "invoice.pdf")

    assert res["doc_type"] == "invoice"
    assert res["sensitivity_level"] == "confidential"
    assert res["content_features"]["page_count"] == 1
    assert mock_complete.call_args.kwargs["json_mode"] is True
