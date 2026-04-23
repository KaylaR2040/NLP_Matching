# Local Setup

## Prerequisites

- Python 3.11+
- Flutter SDK 3.11+
- Git

## 1. Clone and Navigate

```bash
git clone https://github.com/YOUR-ORG/NLP_Matching.git
cd NLP_Matching
```

## 2. Python Virtual Environment (Backend)

```bash
cd wrapper/backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> **Note:** `requirements.txt` includes `torch` and `sentence-transformers`. The first install will download ~2 GB of packages. This is normal.

## 3. Create a Local .env File

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```env
# Generate hashes with:
#   python scripts/generate_password_hash.py --password "yourpassword"
WRAPPER_USER_USERNAME=admin
WRAPPER_USER_PASSWORD_HASH=<generated hash>
WRAPPER_DEV_USERNAME=dev
WRAPPER_DEV_PASSWORD_HASH=<generated hash>

# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
WRAPPER_TOKEN_SECRET=<64-char hex>

# For local file-mode (no Neon required):
WRAPPER_MENTOR_STORAGE_MODE=file

# For local Neon connection (optional):
# WRAPPER_MENTOR_STORAGE_MODE=postgres
# DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require

WRAPPER_REQUIRE_HTTPS=false
WRAPPER_ALLOWED_ORIGINS=http://localhost:8080,http://localhost:3000
```

## 4. Run the Backend Locally

```bash
# From wrapper/backend/
uvicorn app.main:app --reload --port 8000
```

Test it:
```bash
curl http://localhost:8000/health
# → {"status": "ok", ...}

curl http://localhost:8000/config/orgs
# → ["1911 Consulting", "Acappology", ...]
```

## 5. Run the Admin Flutter UI Locally

```bash
cd wrapper/flutter_wrapper
flutter pub get
flutter run -d chrome \
  --dart-define=WRAPPER_API_BASE_URL=http://localhost:8000
```

## 6. Run flutter_mentor / flutter_mentee Locally

```bash
cd flutter_mentor
flutter pub get
flutter run -d chrome \
  --dart-define=BACKEND_CONFIG_URL=http://localhost:8000
```

```bash
cd flutter_mentee
flutter pub get
flutter run -d chrome \
  --dart-define=BACKEND_CONFIG_URL=http://localhost:8000
```

## 7. Connect to Neon Locally (Optional)

If you want to test Neon locally instead of file-mode:

```env
WRAPPER_MENTOR_STORAGE_MODE=postgres
DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require
```

Then initialize the schema:
```bash
# From repo root
python wrapper/backend/scripts/init_schema.py --database-url "$DATABASE_URL"
python wrapper/backend/scripts/seed_config_lists.py --database-url "$DATABASE_URL"
```

## 8. Test Excel Upload and Matching

1. Start the backend locally (`uvicorn app.main:app --reload`)
2. Log in via the admin Flutter UI
3. On the Matching Dashboard, upload a CSV/XLSX of mentees
4. Click "Run Match"

The first run will be slow (~30–120 seconds) because `sentence-transformers` must download the model on first use locally. Subsequent runs are fast. The model is cached at `~/.cache/huggingface/hub/`.

> **Tip:** To pre-download the model without running a match:
> ```bash
> python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"
> ```

## 9. Keep nlp_project/ in sync inside wrapper/backend/

If you edit `nlp_project/` source code, you must re-copy it:

```bash
python wrapper/backend/scripts/prepare_vercel_bundle.py
```

This updates `wrapper/backend/nlp_project/` which is what the backend (and Docker image) actually runs.
