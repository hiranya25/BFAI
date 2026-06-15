from app.services.rag import synthesize_node

def test_rag_no_results():
    state = {
        "query": "What is the secret?",
        "conversation_history": [],
        "retrieved_chunks": [],
        "answer": "",
        "citations": []
    }
    new_state = synthesize_node(state)
    assert "couldn't find any relevant information" in new_state["answer"]
    assert len(new_state["citations"]) == 0

def test_rag_weak_scores():
    state = {
        "query": "What is the secret?",
        "conversation_history": [],
        "retrieved_chunks": [
            {
                "score": 2.0,  # MAX_RETRIEVAL_DISTANCE is 1.35
                "text": "Some completely unrelated text about apples.",
                "filename": "apples.pdf",
                "page_num": 1,
                "image_path": "apples.jpg"
            }
        ],
        "answer": "",
        "citations": []
    }
    new_state = synthesize_node(state)
    assert "don't contain enough information" in new_state["answer"]
    assert len(new_state["citations"]) == 0
