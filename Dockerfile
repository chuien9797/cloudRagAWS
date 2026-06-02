# =========================================================
# BASE — slim Python, no extras
# =========================================================
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Tells sentence-transformers / huggingface_hub where to cache models.
    # Baking this into the image layer means the first request isn't cold.
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence_transformers \
    HF_HOME=/app/.cache/huggingface

# =========================================================
# SYSTEM DEPS
# Keeps the layer small — only what's needed to build wheels.
# =========================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# =========================================================
# STEP 1 — PIN CPU-ONLY TORCH BEFORE ANYTHING ELSE
#
# sentence-transformers depends on torch but doesn't pin the build variant.
# If torch isn't already installed when pip processes requirements.txt it will
# pull the default wheel — which on PyPI is the CUDA build (~2 GB).
#
# Installing the CPU wheel first means pip sees torch as "already satisfied"
# and skips the CUDA download entirely.
# torch 2.3.1+cpu ≈ 210 MB  vs  torch 2.3.1 (CUDA) ≈ 2 100 MB
# =========================================================
RUN pip install --upgrade pip && \
    pip install \
        torch==2.3.1+cpu \
        torchvision==0.18.1+cpu \
        --index-url https://download.pytorch.org/whl/cpu

# =========================================================
# STEP 2 — INSTALL REMAINING DEPENDENCIES
# torch is already present so sentence-transformers won't re-pull it.
# =========================================================
COPY requirements.txt .
RUN pip install -r requirements.txt

# =========================================================
# STEP 3 — PRE-DOWNLOAD THE EMBEDDING MODEL AT BUILD TIME
#
# Bakes all-MiniLM-L6-v2 into the image so the first /upload or /ask
# request doesn't block while the model downloads (~90 MB).
# Remove this step if you prefer to pull at runtime (saves image size).
# =========================================================
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('all-MiniLM-L6-v2')"

# =========================================================
# STEP 4 — NLTK DATA
# =========================================================
RUN python -c "\
import nltk; \
nltk.download('punkt'); \
nltk.download('punkt_tab')"

# =========================================================
# SOURCE CODE
# =========================================================
COPY . .

# =========================================================
# PORT + ENTRYPOINT
# =========================================================
EXPOSE 8000
CMD ["uvicorn", "services.rag_api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]