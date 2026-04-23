# API Reference

Base URL: `https://YOUR-SERVICE.onrender.com` (set `WRAPPER_API_BASE_URL` in Flutter).

All protected endpoints require a `Authorization: Bearer <token>` header.

Auth levels:
- **None** — public, no token required
- **User** — requires valid bearer token
- **Dev** — requires bearer token with `is_dev: true`

---

## Health & Info

### GET /
**Auth:** None

Returns basic service info.

```json
{"status": "ok", "service": "NLP Mentor Matcher Wrapper API", "health": "/health"}
```

### GET /health
**Auth:** None

Returns health status. Used as Render health check.

```json
{"status": "ok"}
```

---

## Authentication

### POST /login
**Auth:** None

```json
// Request
{"username": "string", "password": "string"}

// Response 200
{
  "token": "string",
  "is_dev": false,
  "expires_at": 1234567890.0
}

// Response 401
{"detail": "Invalid credentials"}
```

### GET /me
**Auth:** User

Returns current session info.

```json
{"username": "string", "is_dev": false, "expires_at": 1234567890.0}
```

### POST /token/refresh
**Auth:** User

Returns a new token with a fresh TTL.

```json
{"token": "string", "is_dev": false, "expires_at": 1234567890.0}
```

### POST /logout
**Auth:** User

Invalidates the current token. Returns `{"status": "ok"}`.

---

## Public Config Lists

No authentication required. Used by flutter_mentor and flutter_mentee.

### GET /config/{key}
**Auth:** None

Returns a sorted JSON array of strings.

Valid keys: `orgs`, `concentrations`, `grad-programs`, `abm-programs`, `phd-programs`

```json
// GET /config/orgs
["1911 Consulting", "Acappology", "Accounting Society", ...]

// GET /config/concentrations
["AI/ML", "Annalog Circuits", "Biomedical Instrumentation", ...]
```

**Errors:**
- `404` — Unknown key

---

## Matching

### POST /run_match
**Auth:** User

Runs the NLP mentor–mentee matching pipeline.

**Request:** `multipart/form-data`
- `mentee_file` (required): CSV, XLSX, or XLS file of mentees
- `mentor_file` (optional): CSV, XLSX, or XLS file of mentors. If omitted, uses the mentor manager database.
- `payload_json` (optional): JSON string with match constraints:

```json
{
  "excluded_mentee_ids": [],
  "excluded_mentor_ids": [],
  "rejected_pairs": [{"mentee_id": "m1", "mentor_id": "mr1"}],
  "locked_pairs": [],
  "global_weights": {"industry": 1.5},
  "mentee_weight_overrides": {},
  "top_n": 50
}
```

**Response 200:**
```json
{
  "status": "ok",
  "result": {
    "summary": {
      "mentees_input": 20,
      "mentors_input": 15,
      "assignments": 15
    },
    "assignments": [
      {
        "mentee_id": "string",
        "mentee_name": "string",
        "mentor_id": "string",
        "mentor_name": "string",
        "match_score": 0.87,
        "match_percent": 87,
        "match_band": "Excellent",
        "match_reason": "string",
        "locked": false
      }
    ],
    "top_ranked_pairs": [...]
  },
  "stdout": "string",
  "mentor_source": "mentor_manager"
}
```

**Errors:**
- `400` — Invalid file format or missing mentee file
- `504` — Matching timed out (increase `WRAPPER_MATCH_TIMEOUT_SECONDS`)
- `500` — Matching pipeline failed (check `stdout` and `stderr` in response)

### POST /export_assignments
**Auth:** User

Generates and downloads an XLSX file from the provided rows.

```json
// Request
{
  "rows": [
    {"mentee_name": "Jane", "mentor_name": "Bob", "match_percent": 87}
  ],
  "filename": "final_assignments.xlsx"
}
```

**Response:** XLSX file download (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)

---

## Match History

### GET /match-results
**Auth:** Dev

Returns list of recent match runs (postgres mode only).

Query params: `limit` (default 20, max 100)

```json
[
  {
    "id": 1,
    "run_at": "2026-04-23T14:30:00",
    "run_by": "devaccount",
    "mentee_source": "mentees_spring2026.csv",
    "mentor_source": "mentor_manager",
    "summary": {"assignments": 15, "mentees_input": 20}
  }
]
```

### GET /match-results/{id}
**Auth:** Dev

Returns full detail for a single match run.

```json
{
  "id": 1,
  "run_at": "2026-04-23T14:30:00",
  "run_by": "devaccount",
  "mentee_source": "string",
  "mentor_source": "string",
  "summary": {},
  "assignments": [],
  "top_ranked_pairs": [],
  "stdout": "string"
}
```

---

## Mentors

### GET /mentors
**Auth:** None

Query params: `q`, `active_only` (bool), `has_linkedin` (bool), `company`, `location`, `offset`, `limit`

```json
{
  "items": [{ /* MentorRecord */ }],
  "total": 45
}
```

### GET /mentors/{mentor_id}
**Auth:** None

Returns a single mentor record.

### POST /mentors
**Auth:** Dev

Create a mentor. Request body: mentor fields as JSON.

### PUT /mentors/{mentor_id}
**Auth:** Dev

Update a mentor. Request body: partial mentor fields.

### DELETE /mentors/{mentor_id}
**Auth:** Dev

Soft-deletes a mentor (sets `is_active=false`).

### POST /mentors/import-csv
**Auth:** Dev

**Request:** `multipart/form-data` with `file` (CSV or XLSX)

```json
// Response
{
  "rows_read": 50,
  "added": 45,
  "reactivated": 2,
  "duplicates": 3,
  "invalid": 0,
  "errors": []
}
```

### GET /mentors/export-csv
**Auth:** None

Downloads all active mentors as a CSV file.

### GET /mentors/export-xlsx
**Auth:** None

Downloads all active mentors as an XLSX file.

### POST /mentors/bulk-delete
**Auth:** Dev

Bulk soft-delete. Request body: `{"mentor_ids": ["id1", "id2"]}`

### POST /mentors/{mentor_id}/enrich-linkedin
**Auth:** Dev

Triggers LinkedIn enrichment for one mentor. Returns enrichment result.

### GET /mentors/linkedin-enrichment/config
**Auth:** None

Returns current enrichment configuration (provider, enabled status).

---

## Config List Management (Admin)

These require Dev auth and read/write config lists in both the DB (postgres mode) and the filesystem.

### GET /get_orgs
### POST /save_orgs — body: `{"text": "line1\nline2\n..."}`
### GET /get_concentrations
### POST /save_concentrations — body: `{"text": "..."}`
### GET /get_majors
### POST /save_majors — body: `{"text": "..."}`

All return a payload object with `text`, `file_key`, `label`, and optionally `source: "database"`.

### POST /update_orgs
**Auth:** Dev

Runs the `pull_orgs.py` script to fetch fresh org data from NCSU. Returns script output.

### POST /update_concentrations
**Auth:** Dev

Runs the `pull_concentrations.py` script.

---

## Dev File Management

### GET /dev/files
**Auth:** Dev

Lists all editable files with metadata.

### GET /dev/file/{file_key}
**Auth:** Dev

Returns file text and metadata.

### POST /dev/file/save
**Auth:** Dev

Saves file content. Body: `{"file_key": "string", "text": "string"}`

### POST /dev/file/revert-last
**Auth:** Dev

Reverts to the most recent backup. Body: `{"file_key": "string"}`

### POST /dev/file/run-update
**Auth:** Dev

Runs the update script for a file. Body: `{"file_key": "string"}`

### GET /dev/matching-state
**Auth:** Dev

Returns current matching state (locked/rejected pairs, exclusions).
