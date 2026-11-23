from unittest.mock import patch

from app.services.rag import synthesize_node

NO_INFO = "I cannot find the answer in the provided documents."


def _state(chunks):
    return {
        "query": "What is the total?",
        "conversation_history": [],
        "retrieved_chunks": chunks,
        "answer": "",
        "citations": [],
    }


CHUNK = {"score": 0.4, "text": "Total due: $400", "filename": "invoice.pdf", "page_num": 2, "image_path": "x_page_2.jpg"}


def test_rag_no_results():
    new_state = synthesize_node(_state([]))
    assert new_state["answer"] == NO_INFO
    assert new_state["citations"] == []


@patch("app.services.rag.complete")
def test_rag_answer_with_citation(mock_complete):
    mock_complete.return_value = "The total is $400 [invoice.pdf, 2]."
    new_state = synthesize_node(_state([CHUNK]))
    assert "$400" in new_state["answer"]
    assert new_state["citations"] == [{"filename": "invoice.pdf", "page_num": 2, "image_path": "x_page_2.jpg"}]
    assert mock_complete.call_args.kwargs["system"]  # grounding rules sent as system prompt


@patch("app.services.rag.complete")
def test_rag_no_info_answer_has_no_citations(mock_complete):
    mock_complete.return_value = NO_INFO
    new_state = synthesize_node(_state([CHUNK]))
    assert new_state["citations"] == []


@patch("app.services.rag.complete")
def test_rag_llm_unavailable_returns_graceful_message(mock_complete):
    mock_complete.side_effect = RuntimeError("all providers down")
    new_state = synthesize_node(_state([CHUNK]))
    assert "temporarily unavailable" in new_state["answer"]
    assert new_state["citations"] == []
