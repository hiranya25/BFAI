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

## ⚙️ 2. Deploying the Backend (Hugging Face Spaces)

Because the backend requires heavy system-level libraries for OpenCV, DocTR, PyMuPDF, and PyTorch, it needs a lot of RAM. **Hugging Face Spaces** is the perfect choice because they give you 16GB of RAM and 2 vCPUs completely for free!

### Step-by-Step
1. Create a free account at [huggingface.co](https://huggingface.co).
2. Go to [huggingface.co/new-space](https://huggingface.co/new-space).
3. Configure the Space settings exactly as follows:
   - **Space name:** `doc-intel-backend` (or whatever you prefer)
   - **License:** `MIT`
   - **Select the Space SDK:** Click **Docker** and then click **Blank**.
   - **Space Hardware:** Ensure it says **Free** (2 vCPU, 16GB RAM).
4. Click **Create Space**.
5. Once created, click the **Files** tab at the top.
6. Click **Add file** -> **Upload files**.
7. On your computer, open your `BFAI/backend/` folder. Select **EVERYTHING** inside it (the `Dockerfile`, `requirements.txt`, the `app` folder, etc.) and drag them into the browser. **IMPORTANT: DO NOT upload your `.env` file!** *(Do not upload the BFAI folder itself, just the contents inside the backend folder!)*
8. **Set Environment Variables securely:**
   - Go to the **Settings** tab of your Space.
   - Scroll down to **Variables and secrets**.
   - Click **New secret** and add the following keys (make sure you add them as Secrets so they stay hidden!):
     - `GROQ_API_KEY`: (Your Groq API Key)
     - `API_SECRET_KEY`: (The secret password you created earlier)
     - `ENCRYPTION_KEY`: (The Fernet key you generated)
     - `UPLOAD_DIR`: `./data/raw_docs`
     - `THUMBNAIL_DIR`: `./data/thumbnails`
     - `CHROMA_DIR`: `./data/chroma_db`
     - `MAX_UPLOAD_MB`: `20`
     - `ALLOWED_ORIGINS`: `*` *(We will tighten this later after deploying the frontend)*
9. The Space will automatically build and start running. 
10. Once live (it says "Running" at the top), click the three dots at the top right -> **Embed this space** -> and copy your "Direct URL" (e.g., `https://yourusername-doc-intel-backend.hf.space`).

---

## 🖥️ 3. Deploying the Frontend (Vercel)

Vercel is the creator of Next.js and provides the absolute best hosting for it.

### Step-by-Step
1. Log into [Vercel](https://vercel.com) and click **Add New...** -> **Project**.
2. Connect your GitHub repository.
3. Configure the Project settings:
   - **Project Name:** `document-intelligence`
   - **Root Directory:** Edit this and select `frontend`.
   - **Framework Preset:** You MUST manually select `Next.js` from the dropdown (especially if Vercel doesn't auto-detect it after changing the Root Directory). **If you leave it as "Other", your deployment will fail with a "No Output Directory named 'public' found" error.**

4. **Set Environment Variables:**
   Add the following variables:
   - `NEXT_PUBLIC_API_URL`: (Paste your Hugging Face Space Direct URL here, e.g., `https://yourusername-doc-intel-backend.hf.space`)
   - `API_SECRET_KEY`: (The exact same secret password you put in Hugging Face)

5. Click **Deploy**. Vercel will build and deploy the frontend in under 2 minutes.
6. Once live, copy your Vercel frontend URL (e.g., `https://document-intelligence.vercel.app`).

---

## 🔒 4. Securing the Pipeline (Final Step)

Right now, your backend allows connections from anywhere (`*`). Let's lock it down so ONLY your Vercel frontend can talk to it.

1. Go back to your **Hugging Face Space** dashboard.
2. Go to **Settings** -> **Variables and secrets**.
3. Delete the `ALLOWED_ORIGINS` secret and re-add it.
4. Set the value to your Vercel URL (e.g., `https://document-intelligence.vercel.app`). Do not include a trailing slash.
5. Save changes. Hugging Face will automatically restart your backend container.

### 🎉 You're Done!
Your Enterprise Document Intelligence platform is now live, fully encrypted, and securely air-gapped between frontend and backend!

- Open your Vercel URL.
- Go to `/upload` to index some test documents.
- Go to `/chat` to start interrogating your data!
