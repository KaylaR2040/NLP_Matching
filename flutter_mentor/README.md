# flutter_mentor

Mentor registration Flutter web app.

## Backend Configuration

This app reads backend URL from:

- `--dart-define=BACKEND_API_BASE_URL=...`

Used endpoints:
- `GET /config/{key}`
- `POST /public/forms/mentor`

## Local Run

```bash
cd flutter_mentor
flutter pub get
flutter run -d chrome \
  --dart-define=BACKEND_API_BASE_URL=http://localhost:8000
```

## Production Build (Firebase Hosting)

```bash
cd flutter_mentor
flutter build web --release \
  --dart-define=BACKEND_API_BASE_URL=https://api.example.com
```
