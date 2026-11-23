import logging
import threading
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Load env variables BEFORE any app module reads settings.
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from slowapi import Limiter, _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from slowapi.util import get_remote_address  # noqa: E402

from app.api import upload, chat, documents  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.llm import provider_summary  # noqa: E402
from app.core.startup import index_sample_docs, indexing_status  # noqa: E402

logger = logging.getLogger("app")
limiter = Limiter(key_func=get_remote_address)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("LLM configuration: %s", provider_summary())
    # Index sample docs in the background so the port opens immediately
    # (hosting health checks fail if startup blocks for minutes on OCR).
    threading.Thread(target=index_sample_docs, name="sample-indexer", daemon=True).start()
    yield


app = FastAPI(title="DocIntel API", version="1.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,  # auth is via X-API-Key header, never cookies
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(documents.router, prefix="/api")


@app.get("/")
def root():
    return {"service": "DocIntel API", "health": "/health"}


@app.get("/health")
def health():
    summary = provider_summary()
    return {
        "status": "ok",
        "sample_indexing": indexing_status,
        "llm": {
            "groq": summary["primary"]["enabled"],
            "gemini_fallback": summary["fallback"]["enabled"],
        },
    }
