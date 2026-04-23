FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformers model used by nlp_project so that
# the first /run_match call does not have to download ~400MB at request time.
# This bakes the model into the image layer (~420MB extra) in exchange for
# fast, predictable cold starts on Render.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"

COPY . .

# Tell the backend where to find the nlp_project copy that is bundled inside
# this image (copied from wrapper/backend/nlp_project/ via prepare_vercel_bundle.py).
ENV WRAPPER_NLP_PROJECT_DIR=/app/nlp_project

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
