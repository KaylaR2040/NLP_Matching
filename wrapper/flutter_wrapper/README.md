# Flutter Wrapper

This is the UI shell for operations around `nlp_project/main.py`.

## Implemented scaffold

- Login gate with two role routes:
  - standard user => matching dashboard
  - dev user => matching dashboard + dev tools access
- Login is backend-authenticated:
  - Flutter sends credentials to `POST /login`
  - Backend returns bearer token + role
  - Flutter stores only token via `flutter_secure_storage`
  - Flutter can call `POST /token/refresh` to rotate near-expiry tokens
- Matching dashboard scaffold:
  - Upload mentor + mentee files
  - Run + rerun actions against backend
  - Exclusion pair builder
  - Drag-and-drop mentee reassignment between mentor cards
  - `X` break action to unmatched pool + rejected pair memory
  - Lock toggle for keeping pairs fixed across reruns
  - Unmatched pool with drag support
  - Export final board to XLSX
  - Mentor cards display current load vs configured capacity (`assigned/max`)
- Mentors directory:
  - Regular dashboard page
  - Backend-driven mentor browsing with search and filters
  - Card view with photo/avatar fallback and LinkedIn link button
- Mentor manager (dev-only):
  - Add/edit/deactivate mentors with backend persistence
  - CSV import + XLSX export for `mentor_real.csv` workflow compatibility
  - Sync current mentor data back to canonical backend CSV path
  - Per-row + in-editor "Update from LinkedIn" actions via backend endpoint
  - Displays last LinkedIn sync timestamp and profile photo fallback
  - Unsaved-change prompts trigger only on real value changes (not focus)
- Dev dashboard scaffold:
  - Trigger pull actions for orgs and concentrations
  - Edit and save `data/ncsu_orgs.txt`
  - Edit and save `data/concentrations.txt`
  - Edit and save `wrapper/backend/data/majors.txt`
  - View current exclusion/lock state from backend matching state file

## Connect to backend

Backend URL resolution:

- If `--dart-define=WRAPPER_API_BASE_URL=...` is provided, that URL is used.
- Otherwise:
  - localhost frontend => `http://localhost:8000`
  - non-local frontend => same-origin base URL

Credentials are never stored in Dart source. Configure users on backend via `wrapper/backend/.env`.

## Run

```bash
cd wrapper/flutter_wrapper
flutter pub get
flutter run -d chrome
```

Run Flutter web against deployed backend:

```bash
cd wrapper/flutter_wrapper
flutter run -d chrome \
  --dart-define=WRAPPER_API_BASE_URL=https://<your-backend-domain>
```

If Flutter says web is not configured, scaffold web support once:

```bash
cd wrapper/flutter_wrapper
flutter create . --platforms=web
```

Build production web bundle:

```bash
cd wrapper/flutter_wrapper
flutter build web \
  --release \
  --dart-define=WRAPPER_API_BASE_URL=https://<your-backend-domain>
```

## Deploy frontend to Vercel

Use a separate Vercel project for frontend.

- Root Directory: `wrapper/flutter_wrapper`
- Build Command: `bash scripts/vercel_build.sh`
- Output Directory: `build/web`
- Install Command: leave empty/default

Set this environment variable in Vercel:

- `WRAPPER_API_BASE_URL=https://nlpmatchbackend.vercel.app`

Notes:

- Login uses backend `POST /login`, so backend auth env vars must already be configured.
- No API keys should be hardcoded in Dart source; use Vercel Environment Variables.
- Markdown/source files are not publicly served from this deployment because Vercel only serves the built `build/web` output.

## Notes

- This wrapper targets web behavior first (`dart:html` download flow).
- Full behavior details are in `wrapper/FULL_SYSTEM_BLUEPRINT.md`.
- Mentor data is always read/written through backend APIs; no frontend local-file assumptions.
