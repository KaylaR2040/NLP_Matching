# Flutter Wrapper (Admin UI)

This app is the admin/operator UI for login, matching runs, mentor management, and dev tools.

## Backend URL Resolution

`ApiRuntimeConfig` resolves backend URL in this order:

1. `--dart-define=WRAPPER_API_BASE_URL=...`
2. local host fallback when running on localhost: `http://localhost:8000`
3. `WRAPPER_DEFAULT_API_BASE_URL` (default: `https://api.example.com`)
4. browser origin fallback

## Local Run

```bash
cd wrapper/flutter_wrapper
flutter pub get
flutter run -d chrome \
  --dart-define=WRAPPER_API_BASE_URL=http://localhost:8000
```

## Build For Firebase Hosting

```bash
cd wrapper/flutter_wrapper
flutter build web --release \
  --dart-define=WRAPPER_API_BASE_URL=https://api.example.com
```

## Deploy (root-level scripts)

Use repo-root scripts for full multi-site deploy:

```bash
BACKEND_API_BASE_URL=https://api.example.com \
WRAPPER_API_BASE_URL=https://api.example.com \
./scripts/deploy_frontends_firebase.sh
```
