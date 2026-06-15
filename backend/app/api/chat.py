import logging
from time import perf_counter

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List

from app.core.security import validate_api_key
from app.services.rag import retrieve_node, run_rag

router = APIRouter()
logger = logging.getLogger(__name__)


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]  # full conversation history
    query: str


class Citation(BaseModel):
    filename: str
    page_num: int
    image_path: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]


class DebugRagRequest(BaseModel):
    query: str


class DebugChunk(BaseModel):
    text: str
    filename: str
    page_num: int
    image_path: str
    score: float


class DebugRagResponse(BaseModel):
    retrievedChunks: List[DebugChunk]
    citations: List[Citation]
    scores: List[float]


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    api_key: str = Depends(validate_api_key),
):
    start = perf_counter()
    logger.info(
        "Chat request start query_chars=%s history_messages=%s",
        len(body.query),
        len(body.messages),
    )
    # Build conversation history for LLM (exclude current query)
    history = [{"role": m.role, "content": m.content} for m in body.messages]

    result = run_rag(query=body.query, conversation_history=history)
    logger.info(
        "Chat request end citations=%s elapsed_ms=%.1f",
        len(result["citations"]),
        (perf_counter() - start) * 1000,
    )

    return ChatResponse(
        answer=result["answer"],
        citations=[Citation(**c) for c in result["citations"]],
    )


@router.post("/debug-rag", response_model=DebugRagResponse)
async def debug_rag(
    body: DebugRagRequest,
    api_key: str = Depends(validate_api_key),
):
    start = perf_counter()
    logger.info("Debug RAG request start query_chars=%s", len(body.query))
    state = {
        "query": body.query,
        "conversation_history": [],
        "retrieved_chunks": [],
        "answer": "",
        "citations": [],
    }
    retrieved = retrieve_node(state)["retrieved_chunks"]
    citations = []
    seen = set()
    for chunk in retrieved:
        key = (chunk["filename"], chunk["page_num"])
        if key in seen:
            continue
        seen.add(key)
        citations.append({
            "filename": chunk["filename"],
            "page_num": chunk["page_num"],
            "image_path": chunk["image_path"],
        })
    response = DebugRagResponse(
        retrievedChunks=[DebugChunk(**chunk) for chunk in retrieved],
        citations=[Citation(**citation) for citation in citations],
        scores=[chunk["score"] for chunk in retrieved],
    )
    logger.info(
        "Debug RAG request end chunks=%s citations=%s elapsed_ms=%.1f",
        len(response.retrievedChunks),
        len(response.citations),
        (perf_counter() - start) * 1000,
    )
    return response
