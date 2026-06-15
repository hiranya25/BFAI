# Document Intelligence + Agentic RAG

**AI Engineer Intern Assessment · Build Fast with AI**

This project is a full-stack, enterprise-grade Document Intelligence web application. It ingests complex, real-world documents (scanned PDFs, handwritten pages, and image-heavy reports with dense tables), classifies them, and powers an Agentic RAG chatbot that answers questions with exact, image-backed page citations. Security is implemented at every layer.

---

## 🏗 Architecture Overview

The system is decoupled into a **Next.js (TypeScript)** frontend and a **FastAPI (Python)** backend, communicating via REST and Server-Sent Events (SSE).

```text
1. BULK UPLOAD PIPELINE
[Next.js UI] -> Multipart Form -> [FastAPI /api/upload]
  -> Security: MIME verification & Fernet Encryption at Rest
   -> Smart Routing Parser:
       • PyMuPDF (Digital PDFs, fast table/text extraction)
       • Groq Llama 3.2 90B Vision (Scanned Images & Tables to Markdown)
       • DocTR + LLM Post-Correction (Fallback OCR & Handwriting)
  -> Classification: Groq LLM generates structured JSON metadata
  -> Vectorization: sentence-transformers/all-MiniLM-L6-v2
  -> Storage: ChromaDB

2. AGENTIC RAG PIPELINE
[Next.js Chat UI] -> JSON Request -> [FastAPI /api/chat]
  -> LangGraph Orchestrator (Retrieve -> Synthesize)
  -> ChromaDB Semantic Search (Similarity)
  -> Groq Llama 3.1 8B Synthesis (Strictly Grounded, No Hallucination)
  -> Output: Answer string + structured inline citations
  -> UI Render: Clickable thumbnails served securely via /api/pages/{image}
```

---

## ✨ Core Features & Evaluation Criteria Met

### 1. Advanced Document Parser (Tables & Scans)
- **Smart Routing**: Instead of relying on one parser, the system intelligently routes pages. Digital text uses `PyMuPDF`. Scanned images and complex tables are routed to a Multimodal Vision Model (`llama-3.2-90b-vision-preview`), which expertly preserves structure as Markdown tables rather than flat jumbled text.
- **Thumbnails**: Every page is rasterized into a JPEG thumbnail for visual citation backing.

### 2. Multi-Dimensional JSON Classifier
- Uses an LLM to classify uploaded documents across multiple dimensions.
- **Schema includes**: `doc_type` (invoice, contract, etc.), `topics` (list), `content_features` (has_tables, has_handwriting, etc.), `sensitivity_level`, `sensitivity_reason`, and a short `summary`.

### 3. Agentic RAG & Strict Citations
- Implemented using **LangGraph** to create a deterministic Retrieve -> Synthesize pipeline.
- The LLM is strictly prompted to append `[Document_Name, Page_Number]` citations.
- If relevant context is missing, it actively refuses to hallucinate, responding with: *"I cannot find the answer in the provided documents."*

### 4. Chatbot UI & Real-Time Voice Input
- Built with Next.js and TailwindCSS (Glassmorphic UI).
- Includes multi-turn conversation history.
- **Citations**: Citations appear as clickable floating thumbnails. Clicking them expands the full-res source page.
- **Voice Input (Bonus)**: Implemented real-time browser-native Web Speech API voice transcription on the chat page.

### 5. Bulk Upload & Knowledge Base UI
- A dedicated `/upload` page allows multi-file drag-and-drop.
- Shows live Server-Sent Events (SSE) processing status per file (parsing → classifying → indexing).
- **Knowledge Base Sidebar**: Allows users to view indexed documents, their tags, and instantly purge/delete them from the vector store.
- **Sample Docs**: The repository includes 5 diverse sample documents in `backend/sample_docs` that are automatically indexed on first run.

---

## 🔒 Security Decisions

Handling sensitive intellectual property and PII requires a robust threat model. Here is how security was implemented at every layer:

### What was implemented:
- **Upload Layer**: File extensions are completely ignored. Real MIME-type inspection via `python-magic` prevents executable payload uploads. Size limits (`MAX_UPLOAD_MB`) prevent DOS attacks.
- **Storage Layer (Encryption at Rest)**: All raw uploaded files are immediately encrypted on disk using AES-128 via `cryptography.fernet`. The parser only receives a temporary decrypted file in memory, which is immediately purged after processing.
- **Processing Layer (Air-Gapped OCR Fallback)**: By default, the system uses local, on-device PyTorch models (`python-doctr`) for OCR and embedding (`sentence-transformers`). This ensures raw text does not unnecessarily leak to third-party APIs unless required for complex table layout analysis.
- **API / Retrieval Layer**: All API endpoints are protected by an `X-API-Key` middleware. The Next.js frontend utilizes Server-Side API Proxy Routes (`/api/documents`, `/api/chat`) so the secret key is never exposed to the client's browser. CORS is strictly limited to allowed origins.

### What was considered but skipped:
- **Multi-Tenant User Authentication**: Skipped implementing JWTs, Postgres user tables, and per-user Vector namespaces to keep the assessment focused and free-tier friendly.
- **Cloud Object Storage (S3)**: Skipped in favor of local encrypted disk storage to allow the project to be easily cloned and run locally without AWS credentials.

### What I would add with more time:
- **Presigned URLs**: Instead of streaming thumbnails through a proxy API, I would generate short-lived signed URLs for an S3 bucket to offload image serving.
- **Malware Scanning**: Integration with ClamAV on the upload pipeline before allowing a file to touch the parsing logic.
- **Document-Level RBAC**: Role-based access control where different users have different clearance levels matching the document's classified `sensitivity_level`.

---

## 🛠 Setup & Installation

### 1. Prerequisites (System Dependencies)
The backend requires system libraries for PDF and image processing.
```bash
# Ubuntu / Debian
sudo apt-get update
sudo apt-get install -y libgl1 libglib2.0-0 poppler-utils libmagic1
```

### 2. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Generate a secure encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> **Troubleshooting `venv` Issues:** 
> If you ever move the project folder to a new location, your virtual environment paths will break and you will see a `cannot execute: required file not found` error. To fix this, simply delete and recreate the `venv`:
> ```bash
> deactivate && hash -r
> rm -rf venv
> python3 -m venv venv
> source venv/bin/activate
> pip install -r requirements.txt
> ```

Fill in `backend/.env`:
```env
GROQ_API_KEY=your-groq-api-key
API_SECRET_KEY=a-secure-random-string
ENCRYPTION_KEY=the-fernet-key-from-above
UPLOAD_DIR=./data/raw_docs
THUMBNAIL_DIR=./data/thumbnails
CHROMA_DIR=./data/chroma_db
MAX_UPLOAD_MB=20
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Start the Backend Server:
```bash
uvicorn app.main:app --reload
```
*(The backend will automatically index the 5 sample documents into ChromaDB on first startup).*

### 3. Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env.local
```

Fill in `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
API_SECRET_KEY=the-exact-same-value-as-backend-API_SECRET_KEY
```

Start the Frontend Server:
```bash
npm run dev
```

**Access the Application:**
- **Landing Page:** [http://localhost:3000](http://localhost:3000)
- **Chat Interface:** [http://localhost:3000/chat](http://localhost:3000/chat)
- **Bulk Upload:** [http://localhost:3000/upload](http://localhost:3000/upload)

---

## 🌍 Production Deployment

### Backend (Render / Railway)
1. Set Root Directory to `backend`.
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Environment Variables: Provide `GROQ_API_KEY`, `API_SECRET_KEY`, and `ENCRYPTION_KEY`.
5. **Disk (Optional)**: If you use a paid Render tier, add a Persistent Disk mounted at `/opt/render/project/src/backend/data`. Without a persistent disk, uploaded vectors and thumbnails will be wiped on every deployment. (If using the Free tier, this option is hidden, but the system handles it gracefully by auto-indexing sample documents on startup).

### Frontend (Vercel)
1. Import repository to Vercel. Set Root Directory to `frontend`.
2. Set Environment Variables:
   - `NEXT_PUBLIC_API_URL` = `<your-deployed-backend-url>`
   - `API_SECRET_KEY` = `<your-backend-secret>`
3. Deploy. Update the Backend's `ALLOWED_ORIGINS` to include your new Vercel URL.
