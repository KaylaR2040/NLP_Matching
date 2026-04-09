# Wrapper Workspace

This folder isolates the integration layer around your existing matcher.

- `backend/`: FastAPI bridge that accepts Flutter requests and calls `nlp_project/main.py`.
- `flutter_wrapper/`: Flutter Web shell for login, matching dashboard, mentor directory, mentor manager, drag/drop board, and dev dashboard.
- `FULL_SYSTEM_BLUEPRINT.md`: Detailed end-to-end product and technical spec.

## Quick Start

1. Backend
   - `cd wrapper/backend`
   - `python3 -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`
   - `uvicorn app.main:app --reload --port 8000`

2. Flutter Wrapper
   - `cd wrapper/flutter_wrapper`
   - `flutter pub get`
   - `flutter run -d chrome`

The backend calls the existing matcher through:
- `nlp_project/main.py`

No matching logic is duplicated in `wrapper/backend`; it is only an orchestration bridge.

## Mentor Management MVP

- Persistent backend mentor store (file-backed for MVP) via `backend/app/mentor_store.py`
- Backend mentor APIs (auth required, writes dev-only):
  - `GET /mentors`, `GET /mentors/{mentor_id}`
  - `POST /mentors`, `PUT /mentors/{mentor_id}`, `DELETE /mentors/{mentor_id}`
  - `POST /mentors/import-csv`, `GET /mentors/export-csv`, `GET /mentors/export-xlsx`
  - `POST /mentors/sync-to-default-csv`
  - `POST /mentors/{mentor_id}/enrich-linkedin` (provider-based backend enrichment)
- Frontend pages:
  - regular users: Mentors Directory
  - dev users: Mentor Manager (edit/import/export/sync)
  - dev users: Dev Dashboard exclusion/lock state visibility

## Deployment note

Mentor persistence is currently file-backed. In serverless/ephemeral environments, local writes may not be durable. The store is intentionally isolated behind `MentorStore` so it can be replaced with shared storage or a database without changing API contracts.
