# Vercel Deployment Setup

Three Flutter Web apps are deployed on Vercel. The FastAPI backend is on **Render, not Vercel** — see [RENDER_SETUP.md](RENDER_SETUP.md).

## Root Directory Confusion — Read This First

Each Vercel project must have its **Root Directory** set to the specific subfolder of the repo. This is critical:

| Vercel Project | Root Directory | Framework Preset |
|---|---|---|
| Admin UI | `wrapper/flutter_wrapper` | Other |
| Mentor registration | `flutter_mentor` | Other |
| Mentee registration | `flutter_mentee` | Other |

**Do not** set the root to the repo root (`/`) for any Flutter project — that would expose the wrong `pubspec.yaml` and fail the build.

---

## Project 1: Admin Flutter UI (`wrapper/flutter_wrapper`)

### Vercel Settings

| Setting | Value |
|---|---|
| **Root Directory** | `wrapper/flutter_wrapper` |
| **Framework Preset** | Other |
| **Build Command** | `flutter/bin/flutter build web --release --dart-define=WRAPPER_API_BASE_URL=$WRAPPER_API_BASE_URL` |
| **Output Directory** | `build/web` |
| **Install Command** | `flutter/bin/flutter pub get` |

> Vercel doesn't have Flutter pre-installed. You must add it via a build script or use the community buildpack. The simplest approach: add a `build.sh` or use the Vercel Flutter community integration. See note below.

### Installing Flutter on Vercel

Vercel does not natively support Flutter. Use this approach:

**Option A**: Add a custom `install.sh` in `wrapper/flutter_wrapper/`:
```bash
#!/bin/bash
git clone https://github.com/flutter/flutter.git --depth 1 -b stable flutter
flutter/bin/flutter pub get
```

Set:
- Install Command: `bash install.sh`
- Build Command: `flutter/bin/flutter build web --release --dart-define=WRAPPER_API_BASE_URL=$WRAPPER_API_BASE_URL`

**Option B**: Use the [Vercel Flutter Community Template](https://vercel.com/templates/dart/flutter-starter).

### Environment Variables

| Key | Value |
|---|---|
| `WRAPPER_API_BASE_URL` | `https://YOUR-SERVICE.onrender.com` |

### After Deploy

Note the deployed URL (e.g., `https://matching-web-ten.vercel.app`) and add it to `WRAPPER_ALLOWED_ORIGINS` in your Render environment variables.

---

## Project 2: Mentor Registration (`flutter_mentor`)

### Vercel Settings

| Setting | Value |
|---|---|
| **Root Directory** | `flutter_mentor` |
| **Framework Preset** | Other |
| **Build Command** | `flutter/bin/flutter build web --release --dart-define=BACKEND_CONFIG_URL=$BACKEND_CONFIG_URL` |
| **Output Directory** | `build/web` |
| **Install Command** | `bash install.sh` (same Flutter install script as above) |

### Environment Variables

| Key | Value |
|---|---|
| `BACKEND_CONFIG_URL` | `https://YOUR-SERVICE.onrender.com` |

> The Node.js functions in `flutter_mentor/api/` (Google Form submission) are deployed automatically alongside the Flutter web app in the same Vercel project. Vercel detects the `api/` folder and deploys them as serverless functions.

### Node.js Function Environment Variables (for Google Form)

| Key | Value |
|---|---|
| `MENTOR_GOOGLE_FORM_PREFILLED_LINK` | Your Google Form prefilled link (optional override) |
| `MENTOR_GOOGLE_FORM_ENABLED` | `true` |
| `MENTOR_GOOGLE_FORM_REQUIRED` | `true` |

---

## Project 3: Mentee Registration (`flutter_mentee`)

### Vercel Settings

| Setting | Value |
|---|---|
| **Root Directory** | `flutter_mentee` |
| **Framework Preset** | Other |
| **Build Command** | `flutter/bin/flutter build web --release --dart-define=BACKEND_CONFIG_URL=$BACKEND_CONFIG_URL` |
| **Output Directory** | `build/web` |
| **Install Command** | `bash install.sh` (Flutter install script) |

### Environment Variables

| Key | Value |
|---|---|
| `BACKEND_CONFIG_URL` | `https://YOUR-SERVICE.onrender.com` |

### Node.js Function Environment Variables

| Key | Value |
|---|---|
| `MENTEE_GOOGLE_FORM_PREFILLED_LINK` | Your Google Form prefilled link (optional override) |
| `MENTEE_GOOGLE_FORM_ENABLED` | `true` |
| `MENTEE_GOOGLE_FORM_REQUIRED` | `true` |

---

## Redeploying

Push to the connected branch — Vercel auto-deploys. To redeploy manually: Vercel dashboard → project → **Deployments** → **Redeploy**.

## Checking Logs

Vercel dashboard → project → **Deployments** → click a deployment → **Runtime Logs** (for function errors) or **Build Logs** (for build failures).

## Debugging Common Issues

### 404 on all routes
- Flutter web uses hash routing by default. If you see 404s after navigating, check whether `HashUrlStrategy` or `PathUrlStrategy` is configured in `main.dart`. With `PathUrlStrategy`, Vercel needs a rewrite rule:
  ```json
  { "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }
  ```

### CORS error calling Render backend
- Check `WRAPPER_ALLOWED_ORIGINS` in Render includes your exact Vercel URL (no trailing slash).
- The Flutter web app URL must match exactly (including `https://`).

### Config lists not loading from backend
- Check `BACKEND_CONFIG_URL` is set correctly in Vercel (no trailing slash).
- Test: `curl https://YOUR-SERVICE.onrender.com/config/orgs` — should return JSON array.
- If the backend returns `[]`, run the seed script: `python wrapper/backend/scripts/seed_config_lists.py`.

### Build fails — Flutter not found
- Make sure the Flutter install script runs before `flutter build web`.
- Check the Install Command in Vercel is `bash install.sh` (not `npm install`).

### Missing env var
- Vercel env vars are scoped per environment (Development, Preview, Production). Make sure variables are added for **Production** and **Preview** if needed.
