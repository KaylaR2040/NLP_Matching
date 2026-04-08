# Wrapper Workspace

This folder isolates the integration layer around your existing matcher.

- `backend/`: FastAPI bridge that accepts Flutter requests and calls `nlp_project/main.py`.
- `flutter_wrapper/`: New Flutter Web shell for login, matching dashboard, drag/drop board, and dev dashboard.
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
