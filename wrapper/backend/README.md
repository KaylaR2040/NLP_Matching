# Wrapper Backend (FastAPI Bridge)

## Purpose

This service is the bridge between Flutter Web and the existing Python matcher at `nlp_project/main.py`.

## Endpoints

- `GET /health`
  - Health check.

- `POST /login`
  - Body: `{"username":"...","password":"..."}`
  - Verifies backend-stored password hashes and returns bearer token + `is_dev`.

- `GET /me`
  - Requires bearer token.
  - Returns role/session info for current token.

- `POST /token/refresh`
  - Requires bearer token.
  - Rotates token (new access token, old token invalidated).

- `POST /logout`
  - Requires bearer token.
  - Invalidates current user's active sessions.

- `POST /run_match` (multipart form)
  - Requires bearer token.
  - Files: `mentee_file` (required), `mentor_file` (optional; defaults to Mentor Manager store export)
  - Form field: `payload_json` (JSON string)
  - Runs `nlp_project/main.py ... run` and returns the parsed `latest_matches.json`.
  - Response includes mentor capacity metadata (`mentor_capacity`, `mentor_capacity` per row) so UI can show mentee limits.

- `GET /mentors`
  - Requires bearer token.
  - Lists mentors from backend-managed persistent storage.
  - Supports filters/query params: `q`, `active_only`, `has_linkedin`, `company`, `location`, `offset`, `limit`.

- `GET /mentors/{mentor_id}`
  - Requires bearer token.
  - Returns one mentor record.

- `POST /mentors`
  - Requires dev role bearer token.
  - Creates a mentor record.

- `PUT /mentors/{mentor_id}`
  - Requires dev role bearer token.
  - Updates a mentor record.

- `DELETE /mentors/{mentor_id}`
  - Requires dev role bearer token.
  - Soft-deactivates a mentor (sets `is_active=false`).

- `POST /mentors/import-csv` (multipart form)
  - Requires dev role bearer token.
  - Accepts `.csv`, `.xlsx`, and `.xls` mentor spreadsheet uploads.
  - Appends mentors into backend-managed storage.
  - Skips duplicates by normalized email, then normalized full name only when email is missing.
  - Returns import summary counts (`rows_read`, `added`, `skipped_duplicates`, `invalid`, `errors`) plus row-level duplicate/invalid details.

- `GET /mentors/export-csv`
  - Requires bearer token.
  - Exports the current backend mentor dataset as CSV.

- `GET /mentors/export-xlsx`
  - Requires bearer token.
  - Exports the current backend mentor dataset as `.xlsx`.

- `POST /mentors/sync-to-default-csv`
  - Requires dev role bearer token.
  - Deprecated; returns `410` because mentor data is application data, not a repo-backed CSV.

- `POST /mentors/{mentor_id}/enrich-linkedin`
  - Requires dev role bearer token.
  - Uses backend-only enrichment provider abstraction (mock/proxycurl/http).
  - Updates mentor fields when data is returned (partial updates allowed).
  - No LinkedIn scraping is implemented in Flutter frontend.

- `GET /dev/matching-state`
  - Requires dev role bearer token.
  - Returns canonical matching state file summary (rejected pairs, locked pairs, excluded IDs).

- `POST /update_orgs`
  - Requires dev role bearer token.
  - Runs `wrapper/backend/scripts/pull_orgs.py` (or provided script path) and writes `data/ncsu_orgs.txt`.

- `POST /update_concentrations`
  - Requires dev role bearer token.
  - Runs `wrapper/backend/scripts/pull_concentrations.py` (or provided script path) and writes `data/concentrations.txt`.

- `GET /get_orgs`
  - Requires dev role bearer token.
  - Reads `data/ncsu_orgs.txt`.

- `POST /save_orgs`
  - Requires dev role bearer token.
  - Overwrites `data/ncsu_orgs.txt` from manual editor text.

- `GET /get_concentrations`
  - Requires dev role bearer token.
  - Reads `data/concentrations.txt`.

- `POST /save_concentrations`
  - Requires dev role bearer token.
  - Overwrites `data/concentrations.txt` from manual editor text.

- `GET /get_majors`
  - Requires dev role bearer token.
  - Reads majors text from `wrapper/backend/data/majors.txt` (or `MAJORS_PATH`).

- `POST /save_majors`
  - Requires dev role bearer token.
  - Overwrites majors text file.

- `POST /export_assignments`
  - Requires bearer token.
  - Accepts final board rows JSON and returns `.xlsx` download stream.

## `payload_json` Contract for `/run_match`

```json
{
  "excluded_mentee_ids": ["mentee@email.edu"],
  "excluded_mentor_ids": ["mentor@email.com"],
  "rejected_pairs": [
    {"mentee_id": "m1", "mentor_id": "t1"}
  ],
  "locked_pairs": [
    {"mentee_id": "m2", "mentor_id": "t3"}
  ],
  "global_weights": {
    "industry": 4,
    "degree": 3
  },
  "mentee_weight_overrides": {
    "m2": {"industry": 4, "degree": 4}
  },
  "top_n": 50
}
```

## Run

```bash
cd wrapper/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Vercel production entrypoint (used by `vercel.json`):

```python
from app.main import app
```

Local import validation:

```bash
cd wrapper/backend
python -c "from api.index import app; print(app.title)"
```

## Mentor storage

- Mentor application data is isolated behind `app/mentor_store.py`.
- Supported storage modes:
  - `postgres`: production-safe durable storage for mentor records
  - `file`: local/dev fallback only
- Vercel deployments require `postgres`; the backend will refuse silent file fallback in production.
- Backend CSV/XLSX exports are generated on demand from the current mentor store.
- `WRAPPER_MENTOR_SOURCE_CSV_PATH` is optional provenance/fallback data only; it is not the source of truth for mentor records.

## Repo-backed editable files

- Matching/config files such as `concentrations.txt`, `ncsu_orgs.txt`, and `majors.txt` remain separate from mentor data.
- On Vercel, repo-backed files should use GitHub sync for durable edits.
- Dev-file responses expose:
  - `content_source`: `github`, `repo_bundle`, `runtime_override`, or `local_file`
  - `durable_source`: `github`, `local_only`, `runtime_only`, or `not_configured`
- If GitHub sync is not configured in production, writes fail explicitly instead of pretending local edits are durable.

## Secrets and environment

- Keep secrets in `wrapper/backend/.env` (gitignored).
- Start from `wrapper/backend/.env.example`.
- Do not put API keys or passwords in tracked source or markdown files.
- Backend auth uses env vars:
  - `WRAPPER_USER_USERNAME`
  - `WRAPPER_USER_PASSWORD_HASH`
  - `WRAPPER_DEV_USERNAME`
  - `WRAPPER_DEV_PASSWORD_HASH`
- Generate password hashes with:
  - `python wrapper/backend/scripts/generate_password_hash.py --password "<value>"` (default: 310000 iterations)
- Login endpoint includes in-memory rate limiting by IP + username (configurable via env).
- Login errors are generic (`Invalid credentials`) to avoid user enumeration.
- Security audit events are logged for login success/failure, rate-limit blocks, token refresh/logout, and denied dev access attempts.
- Enable `WRAPPER_REQUIRE_HTTPS=true` in deployment so non-local HTTP traffic is rejected.
- Mentor storage/config env vars:
  - `WRAPPER_DATA_DIR`
  - `WRAPPER_BACKEND_ENV_PATH`
  - `WRAPPER_NLP_PROJECT_DIR`
  - `WRAPPER_DEV_RUNTIME_EDIT_DIR` (defaults to `/tmp/nlp_matching_runtime/dev_files`)
  - `WRAPPER_MENTOR_STORAGE_MODE` (`postgres` or `file`)
  - `WRAPPER_MENTOR_DATABASE_URL` (falls back to `DATABASE_URL`)
  - `WRAPPER_MENTOR_STORE_PATH`
  - `WRAPPER_MENTOR_BACKUP_DIR`
  - `WRAPPER_MENTOR_SOURCE_CSV_PATH` (optional local snapshot / fallback lookup path only)
  - `WRAPPER_MATCHING_STATE_PATH`
- Optional GitHub persistence for dev-file edits:
  - `WRAPPER_GITHUB_SYNC_ENABLED`
  - `WRAPPER_GITHUB_SYNC_TOKEN`
  - `WRAPPER_GITHUB_SYNC_REPO` (`owner/repo`)
  - `WRAPPER_GITHUB_SYNC_BRANCH` (default `main`)
  - `WRAPPER_GITHUB_SYNC_TIMEOUT_SECONDS`
  - Sync auto-enables when token + repo are present, even if `WRAPPER_GITHUB_SYNC_ENABLED` is unset.
- LinkedIn enrichment env vars:
  - `WRAPPER_LINKEDIN_ENRICHMENT_ENABLED`
  - `WRAPPER_LINKEDIN_ENRICHMENT_PROVIDER` (`auto`, `proxycurl`, `http`, `duckduckgo`, `mock`)
  - `WRAPPER_LINKEDIN_ENRICHMENT_HARD_DISABLE` (set `true` only to force-disable enrichment)
  - `WRAPPER_LINKEDIN_ENRICH_MIN_INTERVAL_SECONDS`
  - `WRAPPER_LINKEDIN_ENRICHMENT_TIMEOUT_SECONDS`
  - `WRAPPER_LINKEDIN_PROXYCURL_API_KEY` (if using proxycurl)
  - `WRAPPER_LINKEDIN_PROVIDER_BASE_URL` + `WRAPPER_LINKEDIN_PROVIDER_API_KEY` (if using generic http provider)
  - `WRAPPER_LINKEDIN_SEARCH_ENDPOINT` (optional duckduckgo/html endpoint override)
  - `WRAPPER_LINKEDIN_PUBLIC_PHOTO_ENDPOINT_TEMPLATE` (optional avatar/photo fallback, `{slug}` placeholder)
  - `WRAPPER_LINKEDIN_PUBLIC_PHOTO_TIMEOUT_SECONDS` (optional timeout for public photo lookup)
- Concentrations pull env vars:
  - `WRAPPER_CONCENTRATIONS_HTTP_TIMEOUT_SECONDS`
  - `WRAPPER_CONCENTRATIONS_HTTP_MAX_ATTEMPTS`
  - `WRAPPER_CONCENTRATIONS_HTTP_BACKOFF_SECONDS`
- Request logging env vars:
  - `WRAPPER_LOG_LEVEL` (default `INFO`)
  - Logs method/path/status for each request and logs exception traces on failures.

## Vercel deployment notes

- Set Vercel Root Directory to `wrapper/backend`.
- Keep `api/index.py` + `vercel.json` as committed.
- Keep `.python-version` committed so Vercel uses a compatible Python runtime.
- In Vercel Project Settings, set Build Command:
  - `python scripts/prepare_vercel_bundle.py`
  - This copies `../../nlp_project` essentials into `wrapper/backend/nlp_project` during build.
- Configure env vars from `.env.example` in Vercel project settings.
- `run_match` requires `nlp_project/main.py`; if not bundled in deployment, set `WRAPPER_NLP_PROJECT_DIR` to an available path or disable matching endpoints.
- Dev file editor now includes discoverable text/code files under `nlp_project`, `wrapper/backend/app`, and `wrapper/backend/scripts` (markdown excluded).
- File-backed data paths (`data/...`) are not durable in serverless. Use external storage/DB for production persistence.
- Mentor records should use Postgres in production. Repo-backed editable files should use GitHub sync for durable edits.
