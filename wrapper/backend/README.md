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
  - Files: `mentee_file`, `mentor_file` (`.csv`, `.xlsx`, `.xls`)
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
  - Accepts `mentor_real.csv`-style uploads.
  - Upserts by email first, then fallback identity matching.
  - Returns import summary counts (`created`, `updated`, `unchanged`, `skipped`, `errors`).

- `GET /mentors/export-csv`
  - Requires bearer token.
  - Exports mentor data in a `mentor_real.csv`-compatible structure.

- `GET /mentors/export-xlsx`
  - Requires bearer token.
  - Exports mentor data as `.xlsx` using the same mentor export schema.

- `POST /mentors/sync-to-default-csv`
  - Requires dev role bearer token.
  - Writes current mentor export back to canonical backend CSV path.

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

## Mentor storage

- Default persistent mentor store:
  - `wrapper/backend/data/mentors/mentors_store.json`
- Backup snapshots:
  - `wrapper/backend/data/mentors/backups/`
- Canonical CSV path used for sync/export compatibility:
  - `nlp_project/data/mentor_real.csv`

## Persistence limitation and migration path

- Current mentor persistence is file-backed for MVP.
- In serverless/ephemeral deployments, local file writes may not be durable across instances.
- All mentor reads/writes are isolated behind `app/mentor_store.py` so you can later replace it with:
  - a relational DB (Postgres/MySQL),
  - a managed document store,
  - or shared object storage + metadata DB.
- Migration path:
  1. Keep API contracts unchanged.
  2. Replace `MentorStore` implementation with a DB-backed repository.
  3. Run one-time import from `mentors_store.json` / `mentor_real.csv`.

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
  - `WRAPPER_MENTOR_STORE_PATH`
  - `WRAPPER_MENTOR_BACKUP_DIR`
  - `WRAPPER_MENTOR_SOURCE_CSV_PATH`
  - `WRAPPER_MATCHING_STATE_PATH`
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
