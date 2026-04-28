FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HUB_VERBOSITY=error

WORKDIR /app

COPY wrapper/backend/requirements.txt /app/wrapper/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/wrapper/backend/requirements.txt

# Pre-download the sentence-transformers model so first /run_match calls don't fetch it at request time.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Model is baked into the image — disable outbound HuggingFace calls at runtime.
ENV TRANSFORMERS_OFFLINE=1 \
    HF_DATASETS_OFFLINE=1

COPY wrapper/backend /app/wrapper/backend
COPY nlp_project /app/nlp_project

WORKDIR /app/wrapper/backend

ENV WRAPPER_NLP_PROJECT_DIR=/app/nlp_project

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
