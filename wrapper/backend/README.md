# Wrapper Backend (FastAPI Bridge)

## Purpose

This service bridges Flutter web clients to the matching engine in `nlp_project/main.py` and admin data APIs.

## Core Endpoints

- `GET /health`
  - Health check.

- `POST /login`
  - Body: `{"username":"...","password":"..."}`
  - Returns bearer token + role metadata.

- `POST /token/refresh`, `POST /logout`, `GET /me`
  - Session lifecycle endpoints.

- `POST /run_match` (multipart)
  - Requires bearer token.
  - Runs `nlp_project/main.py ... run` and returns parsed matching output.

- `GET /config/{key}`
  - Public config lists used by frontend apps.
  - Valid keys: `orgs`, `concentrations`, `grad-programs`, `abm-programs`, `phd-programs`.

- `POST /public/forms/mentor`
  - Public mentor submission endpoint.
  - Forwards payload to Google Form and returns forwarding status.

- `POST /public/forms/mentee`
  - Public mentee submission endpoint.
  - Forwards payload to Google Form and returns forwarding status.

- Mentor manager/admin APIs
  - `GET/POST/PUT/DELETE /mentors...`
  - `POST /mentors/import-csv`
  - `GET /mentors/export-csv`
  - `GET /mentors/export-xlsx`
  - Dev/config list endpoints (`/get_orgs`, `/save_orgs`, etc.)

## Local Run

```bash
cd wrapper/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Environment

- Copy `.env.example` to `.env` for local use.
- Production Cloud Run deploys should inject sensitive values via Secret Manager.

Required for production auth:
- `WRAPPER_USER_USERNAME`
- `WRAPPER_USER_PASSWORD_HASH`
- `WRAPPER_DEV_USERNAME`
- `WRAPPER_DEV_PASSWORD_HASH`
- `WRAPPER_TOKEN_SECRET`

Required for postgres mode:
- `DATABASE_URL`
- `WRAPPER_MENTOR_STORAGE_MODE=postgres`

## Cloud Run Deployment

Manual deploy:

```bash
# 1) Optional: push required secrets from local .env to Secret Manager
./scripts/upsert_cloud_run_secrets.sh wrapper/backend/.env

# 2) Deploy Cloud Run service
PROJECT_ID=<gcp-project-id> \
REGION=us-central1 \
SERVICE_NAME=nlp-mentor-backend \
WRAPPER_ALLOWED_ORIGINS=https://admin.example.com,https://mentor.example.com,https://mentee.example.com \
./scripts/deploy_backend_cloud_run.sh
```

Auto deploy from `main`:
- Create a Cloud Build trigger on your `main` branch.
- Use `cloudbuild.backend.yaml` as the build config.
- Ensure required Secret Manager entries exist.

## Notes

- Container reads Cloud Run `PORT` automatically.
- Docker image now copies repo-root `nlp_project/` directly into `/app/nlp_project`.
- Matching logic remains in `nlp_project`; backend orchestrates execution and API contracts.
