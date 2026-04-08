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
- Dev dashboard scaffold:
  - Trigger pull actions for orgs and concentrations
  - Edit and save `data/ncsu_orgs.txt`
  - Edit and save `data/concentrations.txt`
  - Edit and save `wrapper/backend/data/majors.txt`

## Connect to backend

By default, `lib/main.dart` uses:

- `http://localhost:8000`

Update `ApiClient(baseUrl: ...)` if needed.

Credentials are never stored in Dart source. Configure users on backend via `wrapper/backend/.env`.

## Run

```bash
cd wrapper/flutter_wrapper
flutter pub get
flutter run -d chrome
```

## Notes

- This wrapper targets web behavior first (`dart:html` download flow).
- Full behavior details are in `wrapper/FULL_SYSTEM_BLUEPRINT.md`.
