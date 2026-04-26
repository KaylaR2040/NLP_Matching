FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install backend dependencies from the wrapper backend requirements file.
COPY wrapper/backend/requirements.txt /app/wrapper/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/wrapper/backend/requirements.txt

# Pre-download the sentence-transformers model used by nlp_project so that
# first /run_match calls do not fetch ~400MB at request time.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy backend source and repo-root nlp_project directly into the image.
COPY wrapper/backend /app/wrapper/backend
COPY nlp_project /app/nlp_project

WORKDIR /app/wrapper/backend

# Backend path to repo-root matcher source inside the container.
ENV WRAPPER_NLP_PROJECT_DIR=/app/nlp_project

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
