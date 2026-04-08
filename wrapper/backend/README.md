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
