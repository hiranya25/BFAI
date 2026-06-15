import os
import warnings
import logging
from time import perf_counter

# Disable ChromaDB telemetry errors and LangChain deprecation warnings
os.environ["ANONYMOUS_TELEMETRY"] = "False"
warnings.filterwarnings("ignore", category=DeprecationWarning)

from typing import TypedDict, List

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, END
from groq import Groq

from app.core.config import get_settings

settings = get_settings()
CHROMA_DIR = settings.chroma_dir
MAX_RETRIEVAL_DISTANCE = 2.0
logger = logging.getLogger(__name__)

# Initialize Groq client
client = Groq(api_key=settings.groq_api_key)

_vectorstore = None

def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )
        _vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
            collection_name="documents",
        )
    return _vectorstore

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=250,
    separators=["\n\n", "\n", ". ", " "],
)


# --- Indexing ---

def index_document(doc_id: str, pages: list, filename: str, classification: dict):
    """Chunk and embed all pages. Store with rich metadata."""
    texts = []
    metadatas = []

    for page in pages:
        page_text = page["text"]

        # Include table content as structured data blocks
        for tbl in page.get("tables", []):
            header_row = " | ".join(str(h) for h in tbl["headers"])
            table_rows = "\n".join(" | ".join(str(c) for c in row) for row in tbl["rows"])
            page_text += f"\n\n[Data Table from Page {page['page_num']}]\n{header_row}\n{table_rows}\n[/Data Table]\n"

        if not page_text.strip():
            continue

        chunks = splitter.split_text(page_text)
        for chunk in chunks:
            texts.append(chunk)
            metadatas.append({
                "doc_id": doc_id,
                "filename": filename,
                "page_num": page["page_num"],
                "image_path": page["image_path"],
                "doc_type": classification.get("doc_type", "other"),
                "sensitivity": classification.get("sensitivity_level", "internal"),
                "ocr_confidence": page.get("confidence_score", 1.0),
                "extraction_method": page.get("extraction_method", "unknown")
            })

    if texts:
        get_vectorstore().add_texts(texts=texts, metadatas=metadatas)


def list_documents() -> list:
    """Returns a list of unique documents with aggregated metadata from ChromaDB."""
    try:
        store = get_vectorstore()
        collection = store._collection
        data = collection.get(include=["metadatas"])
        
        docs = {}
        for meta in data.get("metadatas", []):
            if not meta:
                continue
            doc_id = meta.get("doc_id")
            if not doc_id:
                continue
                
            if doc_id not in docs:
                docs[doc_id] = {
                    "doc_id": doc_id,
                    "filename": meta.get("filename", "Unknown"),
                    "doc_type": meta.get("doc_type", "unknown"),
                    "sensitivity": meta.get("sensitivity", "unknown"),
                    "page_count": 0,
                    "chunk_count": 0
                }
            
            docs[doc_id]["chunk_count"] += 1
            page_num = meta.get("page_num", 1)
            if page_num > docs[doc_id]["page_count"]:
                docs[doc_id]["page_count"] = page_num
                
        return list(docs.values())
    except Exception as e:
        logger.exception("Failed to list documents: %s", e)
        return []

def delete_document(doc_id: str) -> bool:
    """Deletes all chunks for a given doc_id from ChromaDB and removes the raw/thumbnail files."""
    try:
        store = get_vectorstore()
        collection = store._collection
        collection.delete(where={"doc_id": doc_id})
        
        from app.core.config import get_settings
        settings = get_settings()
        enc_file = settings.upload_dir / f"{doc_id}.enc"
        if enc_file.exists():
            enc_file.unlink()
            
        for thumb in settings.thumbnail_dir.glob(f"{doc_id}_page_*.jpg"):
            thumb.unlink()
            
        return True
    except Exception as e:
        logger.exception("Failed to delete document %s: %s", doc_id, e)
        return False



# --- LangGraph RAG Agent ---

class AgentState(TypedDict):
    query: str
    conversation_history: List[dict]
    retrieved_chunks: List[dict]
    answer: str
    citations: List[dict]


def retrieve_node(state: AgentState) -> AgentState:
    """Semantic search — top 6 most relevant chunks."""
    stage_start = perf_counter()
    logger.info("RAG STAGE 1 question received chars=%s", len(state["query"]))
    query = state["query"].strip()
    if not query:
        state["retrieved_chunks"] = []
        logger.info("RAG STAGE 4 retrieved chunk count=0 elapsed_ms=%.1f", (perf_counter() - stage_start) * 1000)
        return state

    try:
        search_start = perf_counter()
        # Fails safely if ChromaDB is completely empty
        logger.info("RAG STAGE 2 query embedding/search started")
        results = get_vectorstore().similarity_search_with_score(
            query, k=3
        )
        logger.info("RAG STAGE 3 vector search completed elapsed_ms=%.1f", (perf_counter() - search_start) * 1000)
    except Exception as e:
        logger.exception("Chroma search failed or is empty: %s", e)
        results = []

    chunks = []
    for doc, score in results:
        chunks.append({
            "text": doc.page_content,
            "filename": doc.metadata.get("filename", "unknown"),
            "page_num": doc.metadata.get("page_num", 1),
            "image_path": doc.metadata.get("image_path", ""),
            "score": round(score, 3),
        })
    state["retrieved_chunks"] = chunks
    logger.info(
        "RAG STAGE 4 retrieved chunk count=%s scores=%s elapsed_ms=%.1f",
        len(chunks),
        [chunk["score"] for chunk in chunks],
        (perf_counter() - stage_start) * 1000,
    )
    return state


def synthesize_node(state: AgentState) -> AgentState:
    """Build grounded answer with inline citations."""
    stage_start = perf_counter()
    chunks = state["retrieved_chunks"]

    if not chunks:
        state["answer"] = "I cannot find the answer in the provided documents."
        state["citations"] = []
        logger.info("RAG STAGE 5 citation extraction skipped no_chunks elapsed_ms=%.1f", (perf_counter() - stage_start) * 1000)
        return state

    # Build context block
    context_parts = []
    for i, chunk in enumerate(chunks):
        context_parts.append(
            f"[Source {i+1}: {chunk['filename']}, p. {chunk['page_num']}]\n{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    system = """You are a highly rigorous document analyst. Answer the user's question using STRICTLY and SOLELY the provided context chunks.

Rules:
1. Rely strictly and solely on the provided context chunks. Do not use outside knowledge.
2. For every answer or claim generated, enforce the inline citation format exactly using metadata: [Document_Name, Page_Number]. (e.g. [invoice.pdf, 2]).
3. If the answer cannot be found in the context chunks, reply precisely with: "I cannot find the answer in the provided documents." Prevent any hallucination.
4. Keep answers concise and direct."""

    messages_text = ""
    for m in state["conversation_history"][-4:]:
        messages_text += f"{m['role'].capitalize()}: {m['content']}\n"

    prompt = f"""{system}

Conversation History:
{messages_text}

Context from documents:
{context}

Question: {state['query']}
"""

    try:
        llm_start = perf_counter()
        logger.info("RAG STAGE 6 LLM synthesis started chunks=%s prompt_chars=%s", len(chunks), len(prompt))
        
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
        )
        answer = completion.choices[0].message.content
        
        if not answer:
            raise RuntimeError("LLM returned an empty answer.")
        logger.info("RAG STAGE 6 LLM synthesis completed elapsed_ms=%.1f", (perf_counter() - llm_start) * 1000)
    except Exception as e:
        logger.exception("RAG STAGE 6 LLM synthesis failed: %s", e)
        state["answer"] = "We found relevant information, but the AI response service is temporarily unavailable."
        state["citations"] = []
        logger.info("RAG STAGE 7 response returned fallback elapsed_ms=%.1f", (perf_counter() - stage_start) * 1000)
        return state

    seen = set()
    citations = []

    # If the LLM gave the fallback no-info response, return no citations.
    no_info_phrase = "I cannot find the answer in the provided documents."
    if no_info_phrase.lower() in answer.lower():
        state["answer"] = answer
        state["citations"] = []
        return state

    for chunk in chunks:
        # Check if the LLM cited this chunk's filename in the answer
        if chunk["filename"] in answer:
            key = (chunk["filename"], chunk["page_num"])
            if key in seen:
                continue
            seen.add(key)
            citations.append({
                "filename": chunk["filename"],
                "page_num": chunk["page_num"],
                "image_path": chunk["image_path"],
            })

    if not citations:
        logger.warning("LLM answer did not include parseable source filenames; attaching top retrieved citations.")
        for chunk in chunks[:3]:
            key = (chunk["filename"], chunk["page_num"])
            if key in seen:
                continue
            seen.add(key)
            citations.append({
                "filename": chunk["filename"],
                "page_num": chunk["page_num"],
                "image_path": chunk["image_path"],
            })

    state["answer"] = answer
    state["citations"] = citations
    logger.info(
        "RAG STAGE 5 citation extraction completed count=%s",
        len(citations),
    )
    logger.info("RAG STAGE 7 response returned elapsed_ms=%.1f", (perf_counter() - stage_start) * 1000)
    return state


def build_rag_graph():
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("synthesize", synthesize_node)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


rag_agent = build_rag_graph()


def run_rag(query: str, conversation_history: list) -> dict:
    result = rag_agent.invoke({
        "query": query,
        "conversation_history": conversation_history,
        "retrieved_chunks": [],
        "answer": "",
        "citations": [],
    })
    return {
        "answer": result["answer"],
        "citations": result["citations"],
    }
