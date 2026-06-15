from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

# Load env variables BEFORE any module imports so that genai.configure() picks up GEMINI_API_KEY
load_dotenv()

from app.api import upload, chat, documents
from app.core.config import get_settings
from app.core.startup import index_sample_docs

limiter = Limiter(key_func=get_remote_address)
settings = get_settings()

app = FastAPI(title="DocIntel API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(documents.router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """Index sample docs on first run if Chroma is empty."""
    await index_sample_docs()

@app.get("/health")
def health():
    return {
        "status": "ok",
    }
