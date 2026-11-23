---
title: DocIntel Backend
emoji: 📄
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# DocIntel Backend (FastAPI)

Document parsing, classification and Agentic RAG API for the Document Intelligence app.
This folder is self-contained and is what gets deployed (e.g. as a Hugging Face Docker Space).
The YAML header above is the Hugging Face Space configuration — keep it.

- Health check: `GET /health` (no auth) — also reports sample-indexing progress and which LLM providers are configured.
- All `/api/*` routes require the `X-API-Key` header.

LLM routing: Groq is tried first (`GROQ_MAX_ATTEMPTS`, default 3); Gemini is the fallback.
See [`.env.example`](./.env.example) for every setting and the repository-level `DEPLOY.md` for deployment steps.
