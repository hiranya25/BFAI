# Production Deployment Guide

Recommended topology:

| Part | Host | Why |
|---|---|---|
| **Backend** (FastAPI, `backend/`) | **Hugging Face Spaces — Docker** (free CPU: 2 vCPU / 16 GB RAM) | PyTorch OCR + embeddings need ~3–4 GB RAM; 512 MB free tiers (Render/Heroku) crash. |
| **Frontend** (Next.js, `frontend/`) | **Vercel** | Native Next.js hosting; the API routes keep the backend secret server-side. |

Fallback backend host if Hugging Face refuses the free tier or you need data that survives restarts: **Railway** (section 5).

---

## 1. Prepare secrets (once)

Run locally and keep the output somewhere safe (password manager):

```bash
# API secret shared by frontend and backend
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Fernet key for encryption at rest — keep it stable; changing it makes stored files unreadable
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

LLM keys — get both (Groq is primary, Gemini is the automatic fallback):

- Groq: <https://console.groq.com/keys>
- Gemini: <https://aistudio.google.com/apikey>

---

## 2. Backend → Hugging Face Space (Docker)

1. Create a Space at <https://huggingface.co/new-space>:
   - **SDK:** Docker → *Blank*
   - **Hardware:** CPU basic (free)
   - **Visibility:** Public is fine — the API rejects requests without the API key. (A *private* Space is not reachable from Vercel.)
2. Upload the **contents of `backend/`** (not the folder itself), **excluding `data/` and any `.env`**:
   - **CLI (recommended, handles exclusions and binary files):**
     ```bash
     pip install -U huggingface_hub
     hf auth login
     hf upload <your-username>/<space-name> backend . --repo-type space --exclude "data/*" ".env" "venv/*" "__pycache__/*"
     ```
   - **or Web UI:** *Files → Add file → Upload files*, drag everything inside `backend/` **except** `data/` and `.env`.
   - `backend/README.md` carries the Space config (`sdk: docker`, `app_port: 7860`) — upload it too.
3. **Settings → Variables and secrets.** Add as **Secrets**:

   | Name | Value |
   |---|---|
   | `GROQ_API_KEY` | your Groq key |
   | `GEMINI_API_KEY` | your Gemini key |
   | `API_SECRET_KEY` | the API secret from step 1 |
   | `ENCRYPTION_KEY` | the Fernet key from step 1 |

   Optional **Variables** (defaults shown — change only to swap models after a deprecation):
   `GROQ_TEXT_MODEL=openai/gpt-oss-20b`, `GROQ_VISION_MODEL=qwen/qwen3.8-27b`, `GEMINI_MODEL=gemini-3.8-flash`,
   `GROQ_MAX_ATTEMPTS=3`, `MAX_UPLOAD_MB=20`, `ALLOWED_ORIGINS=https://<your-vercel-app>.vercel.app`.
4. The first build takes ~10–15 min (it bakes the OCR/embedding models into the image). When the status is **Running**, open
   `https://<username>-<space-name>.hf.space/health`. Expect:
   ```json
   {"status":"ok","sample_indexing":{"state":"running",...},"llm":{"groq":true,"gemini_fallback":true}}
   ```
   `sample_indexing.state` becomes `done` after a few minutes (the 5 sample docs are indexed in the background).

> **Free Spaces have an ephemeral disk.** Uploaded documents are lost on every restart/rebuild, and the Space sleeps after 48 h without traffic (the next visit wakes it, ~1 min). The sample docs re-index automatically. For persistence, add paid *Persistent storage* and set `UPLOAD_DIR=/data/raw_docs`, `THUMBNAIL_DIR=/data/thumbnails`, `CHROMA_DIR=/data/chroma_db` — or use Railway (section 5).

---

## 3. Frontend → Vercel

1. <https://vercel.com/new> → import the GitHub repo.
2. **Root Directory:** `frontend`. **Framework Preset:** Next.js (select it manually if it shows "Other").
3. **Environment Variables:**

   | Name | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://<username>-<space-name>.hf.space` (no trailing slash) |
   | `API_SECRET_KEY` | same value as the backend |
   | `APP_PASSWORD` | *(recommended)* a password for the site — see note below |
   | `NEXT_PUBLIC_MAX_UPLOAD_MB` | `4` (Vercel rejects request bodies over ~4.5 MB) |

4. **Deploy**, then open the URL → `/chat` and ask about a sample document (e.g. *"What is in the security checklist?"*).

> **Why `APP_PASSWORD`:** the frontend's API routes attach the backend secret for every visitor, so without it anyone with the link can upload and **delete** documents. With it set, the browser asks for a login (user `admin` or `APP_USERNAME`).
>
> **Limits on Vercel Hobby:** uploads ≤ 4 MB per file; each upload request may run ≤ 300 s (`maxDuration`). Very large scanned PDFs can exceed that — the document may still finish indexing on the backend; reopen the Knowledge Base to check. Vercel Hobby is for non-commercial use; use Pro for company/commercial use.

---

## 4. Lock down CORS (optional)

Browsers never call the backend directly (all calls go through Vercel server routes), so CORS is defence-in-depth. Set the Space variable `ALLOWED_ORIGINS` to your Vercel URL, e.g. `https://document-intelligence.vercel.app` (no trailing slash). The Space restarts automatically.

---

## 5. Alternative backend host: Railway (persistent disk)

1. New Project → *Deploy from GitHub repo* → set **Root Directory** to `backend` (Railway detects the `Dockerfile`).
2. Add the same secrets as in section 2, plus `RAILWAY_RUN_UID=0` (Railway volumes are root-owned).
3. Add a **Volume** mounted at `/home/user/app/data` — uploads and the vector DB then survive redeploys.
4. Use an instance with **≥ 4 GB RAM**. Railway injects `$PORT`; the Dockerfile honours it.
5. Generate a public domain and use it as `NEXT_PUBLIC_API_URL` on Vercel.

---

## 6. LLM routing & operations

- Every LLM call (classification, RAG answers, OCR clean-up, scanned-page vision) goes through `backend/app/core/llm.py`:
  Groq up to `GROQ_MAX_ATTEMPTS` (default **3**, backoff 1 s/2 s) → Gemini fallback (`GEMINI_MAX_ATTEMPTS`, default 2).
  Non-retryable Groq errors (invalid request, bad key, model not found/decommissioned) skip straight to Gemini.
- Groq currently has **no production vision model**; `GROQ_VISION_MODEL` defaults to a preview model. If Groq removes it, calls fall through to Gemini automatically — or set `GROQ_VISION_MODEL=` (empty) to skip Groq for images.
- When a provider deprecates a model, change the model variable in the host settings and restart — no code change.
- Logs show `LLM ok purpose=… provider=groq|gemini attempt=…` and `LLM fallback … groq->gemini`, so you can see when the fallback is carrying traffic. Prompt and document text is never logged.
- Run the backend tests in the built image: `docker run --rm --entrypoint sh <image> -c "pip install --user -q pytest && python -m pytest -q"`.
