# Production Deployment Guide

This guide details the exact steps to deploy the **Document Intelligence + Agentic RAG** platform to production cloud environments for free (or extremely cheap). We recommend deploying the Backend to **Render.com** and the Frontend to **Vercel**.

---

## 🏗️ 1. Preparing for Deployment

Before deploying, you need to generate your production secrets.

1. **Generate an Encryption Key:**
   Run this command locally to generate a secure Fernet key for encrypting documents at rest:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   *Save this key, you will need it for the Backend deployment.*

2. **Generate an API Secret Key:**
   Create a strong, random password. This will authenticate your Frontend and Backend together. (e.g., `super-secret-doc-intel-key-2026`).

3. **Get your Groq API Key:**
   Make sure you have an active API key from the [Groq Console](https://console.groq.com).

---

## ⚙️ 2. Deploying the Backend (Render.com)

Since the backend requires system-level libraries for OpenCV, DocTR, and PyMuPDF, Render is an excellent choice.

### Step-by-Step
1. Push your entire project to a **GitHub repository**.
2. Log into [Render.com](https://render.com) and click **New+** -> **Web Service**.
3. Connect your GitHub repository.
4. Configure the Web Service settings exactly as follows:
   - **Name:** `doc-intel-backend` (or whatever you prefer)
   - **Region:** Choose the region closest to you.
   - **Branch:** `main`
   - **Root Directory:** `backend` *(CRITICAL: Must be exactly this)*
   - **Environment:** `Python 3`
   - **Build Command:**
     ```bash
     apt-get update && apt-get install -y libgl1 libglib2.0-0 poppler-utils libmagic1 && pip install -r requirements.txt
     ```
   - **Start Command:**
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```

5. **Set Environment Variables:**
   Click "Advanced" and add the following variables:
   - `GROQ_API_KEY`: (Your Groq API Key)
   - `API_SECRET_KEY`: (The secret password you created earlier)
   - `ENCRYPTION_KEY`: (The Fernet key you generated)
   - `UPLOAD_DIR`: `./data/raw_docs`
   - `THUMBNAIL_DIR`: `./data/thumbnails`
   - `CHROMA_DIR`: `./data/chroma_db`
   - `MAX_UPLOAD_MB`: `20`
   - `ALLOWED_ORIGINS`: `*` *(We will tighten this later after deploying the frontend)*

6. **Attach a Persistent Disk (CRITICAL):**
   - Click **Advanced** -> **Add Disk**
   - **Name:** `data`
   - **Mount Path:** `/opt/render/project/src/backend/data`
   - **Size:** `1 GB` (or more if needed)
   - *Why? Render wipes the filesystem every time it deploys. If you don't mount a disk here, your ChromaDB vectors and uploaded documents will be permanently deleted every time the server restarts.*

7. Click **Create Web Service**. Wait 5-10 minutes for it to build and start.
8. Once live, copy your backend URL (e.g., `https://doc-intel-backend.onrender.com`).

---

## 🖥️ 3. Deploying the Frontend (Vercel)

Vercel is the creator of Next.js and provides the absolute best hosting for it.

### Step-by-Step
1. Log into [Vercel](https://vercel.com) and click **Add New...** -> **Project**.
2. Connect your GitHub repository.
3. Configure the Project settings:
   - **Project Name:** `document-intelligence`
   - **Framework Preset:** `Next.js` (Should auto-detect)
   - **Root Directory:** Edit this and select `frontend`.

4. **Set Environment Variables:**
   Add the following variables:
   - `NEXT_PUBLIC_API_URL`: (Paste your Render Backend URL here, e.g., `https://doc-intel-backend.onrender.com`)
   - `API_SECRET_KEY`: (The exact same secret password you put in Render)

5. Click **Deploy**. Vercel will build and deploy the frontend in under 2 minutes.
6. Once live, copy your Vercel frontend URL (e.g., `https://document-intelligence.vercel.app`).

---

## 🔒 4. Securing the Pipeline (Final Step)

Right now, your backend allows connections from anywhere (`*`). Let's lock it down so ONLY your Vercel frontend can talk to it.

1. Go back to your **Render Web Service** dashboard.
2. Go to **Environment**.
3. Edit the `ALLOWED_ORIGINS` variable.
4. Replace `*` with your Vercel URL (e.g., `https://document-intelligence.vercel.app`). Do not include a trailing slash.
5. Save changes. Render will automatically restart your backend.

### 🎉 You're Done!
Your Enterprise Document Intelligence platform is now live, fully encrypted, and securely air-gapped between frontend and backend!

- Open your Vercel URL.
- Go to `/upload` to index some test documents.
- Go to `/chat` to start interrogating your data!
