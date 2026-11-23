FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System libraries: OpenCV (libgl1, libglib2.0-0), pdf2image (poppler-utils),
# python-magic (libmagic1). build-essential compiles chroma-hnswlib (no py3.12 wheel).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        poppler-utils \
        libmagic1 \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs containers as UID 1000. Running as that user everywhere
# keeps the app directory and model caches writable on every host.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    DOCTR_CACHE_DIR=/home/user/.cache/doctr \
    ANONYMIZED_TELEMETRY=False
WORKDIR /home/user/app

# CPU-only PyTorch first (avoids ~4GB of unused CUDA libraries), then the rest.
COPY --chown=user requirements.txt .
RUN pip install --user torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --user -r requirements.txt

# Bake model weights into the image so cold starts don't download ~600MB.
COPY --chown=user scripts/preload_models.py scripts/preload_models.py
RUN python scripts/preload_models.py

COPY --chown=user . .
RUN mkdir -p data/raw_docs data/thumbnails data/chroma_db

# Hugging Face Spaces expects 7860; Render/Railway/Fly inject $PORT.
ENV PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860} --proxy-headers --forwarded-allow-ips='*'"]
