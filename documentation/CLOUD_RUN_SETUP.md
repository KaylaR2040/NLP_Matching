# Cloud Run Setup (Backend)

The FastAPI backend runs on Google Cloud Run as a Docker container.

**Free tier:** 2M requests/month + 360,000 GB-seconds of memory/month. At 4 GiB and ~60s per match run, this gives ~1,500 free match runs/month — effectively unlimited for a twice-per-semester ECE program.

For the full ordered setup (do this first), see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

---

## Prerequisites

- `gcloud` CLI installed and logged in
- Docker Desktop installed and running
- GCP project created with billing enabled

Enable required APIs:
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com
```

---

## Required Secrets (Secret Manager)

These 6 values must be stored in Secret Manager before deploying. Pull them from `wrapper/backend/.env`:

```bash
PROJECT_ID=YOUR-GCP-PROJECT-ID \
  ./scripts/upsert_cloud_run_secrets.sh wrapper/backend/.env
```

| Secret name | What it is |
|---|---|
| `DATABASE_URL` | Neon Postgres connection string |
| `WRAPPER_TOKEN_SECRET` | 64-char hex string for signing auth tokens |
| `WRAPPER_USER_USERNAME` | Login username for regular users |
| `WRAPPER_USER_PASSWORD_HASH` | PBKDF2 hash (generate with `scripts/generate_password_hash.py`) |
| `WRAPPER_DEV_USERNAME` | Login username for dev/admin users |
| `WRAPPER_DEV_PASSWORD_HASH` | PBKDF2 hash |

Verify they exist:
```bash
gcloud secrets list --project YOUR-GCP-PROJECT-ID
```

---

## Deploy

```bash
export PROJECT_ID=YOUR-GCP-PROJECT-ID

# Set CORS origins to your Firebase frontend URLs (get these from FIREBASE_SETUP.md)
export WRAPPER_ALLOWED_ORIGINS="https://YOUR-ADMIN-SITE.web.app,https://YOUR-MENTOR-SITE.web.app,https://YOUR-MENTEE-SITE.web.app"

./scripts/deploy_backend_cloud_run.sh
```

What the script does:
1. Creates an Artifact Registry Docker repo (if it doesn't exist)
2. Builds the image from repo root: `docker build -f wrapper/backend/Dockerfile .`
   - Installs Python deps (torch ~2 GB, sentence-transformers)
   - Pre-downloads `all-mpnet-base-v2` model (~420 MB) into the image
   - Copies `nlp_project/` from repo root (no manual bundle step needed)
3. Pushes image to Artifact Registry
4. Deploys Cloud Run revision with:
   - **4 GiB memory** (required for torch + sentence-transformers at inference)
   - **300s request timeout** (matching can take 60–120s on first run)
   - **concurrency = 1** (prevents multiple model loads per instance)
   - **min-instances = 0** (scales to zero when idle — free tier)
   - **max-instances = 3**
   - Public access enabled (auth handled by bearer token in the API)

**First build: 15–20 minutes.** Subsequent deploys: ~3 minutes (Docker layer cache).

At the end, the script prints your service URL:
```
Service URL: https://nlp-mentor-backend-XXXXXXXX-uc.a.run.app
```

---

## Verify

```bash
BACKEND=https://YOUR-SERVICE.a.run.app

curl $BACKEND/health
# → {"status":"ok","service":"NLP Mentor Matcher Wrapper API",...}

curl $BACKEND/config/orgs | head -c 120
# → ["1911 Consulting","Acappella",...] (after Neon seed — see NEON_SETUP.md)

# Test login
curl -s -X POST $BACKEND/login \
  -H "Content-Type: application/json" \
  -d '{"username":"YOUR-USERNAME","password":"YOUR-PASSWORD"}'
# → {"token":"...","is_dev":true,...}
```

---

## Environment Variables

Non-secret vars are passed directly to the Cloud Run revision via `--set-env-vars` in the deploy script. The defaults in the script are:

| Variable | Default in deploy script |
|---|---|
| `WRAPPER_MENTOR_STORAGE_MODE` | `postgres` |
| `WRAPPER_NLP_PROJECT_DIR` | `/app/nlp_project` |
| `WRAPPER_MATCH_TIMEOUT_SECONDS` | `270` |
| `WRAPPER_SCRIPT_TIMEOUT_SECONDS` | `180` |
| `WRAPPER_REQUIRE_HTTPS` | `true` |
| `WRAPPER_ALLOWED_ORIGINS` | Set via `$WRAPPER_ALLOWED_ORIGINS` env var |

To override any of these, set them as shell env vars before running the deploy script.

---

## Auto-Deploy on Push (optional)

Set up a Cloud Build trigger so every push to `main` redeploys the backend automatically:

1. Cloud Console → Cloud Build → Triggers → Create Trigger
2. Source: your GitHub repo, branch `main`
3. Build config: `cloudbuild.backend.yaml`
4. Add substitution variables:
   - `_REGION` = `us-central1`
   - `_SERVICE_NAME` = `nlp-mentor-backend`
   - `_NON_SECRET_ENV_VARS` = (copy from script defaults, update CORS origins)
   - `_SECRET_ENV_VARS` = (copy from script defaults)

---

## Viewing Logs

Cloud Console → Cloud Run → your service → **Logs** tab.

Or via CLI:
```bash
gcloud run services logs read nlp-mentor-backend \
  --project YOUR-PROJECT-ID \
  --region us-central1 \
  --limit 50
```

Key log patterns to search for:
- `cors_config` — shows CORS origins loaded at startup
- `run_match_response` — each match run with duration
- `config_list_db_read_failed` — Neon connection issues
- `ERROR` — any unhandled exceptions

---

## Updating CORS After Frontend Deploy

After deploying Firebase frontends and getting real URLs:

```bash
export PROJECT_ID=YOUR-PROJECT-ID
export WRAPPER_ALLOWED_ORIGINS="https://nlp-admin.web.app,https://nlp-mentor.web.app,https://nlp-mentee.web.app"
./scripts/deploy_backend_cloud_run.sh
```

---

## Troubleshooting

**Build fails — `Dockerfile not found`**
The deploy script runs `docker build -f wrapper/backend/Dockerfile .` from the repo root. Make sure you're running the script from the repo root, not from inside `scripts/`.

**`gcloud: command not found`**
Install Google Cloud CLI: `brew install --cask google-cloud-sdk`

**`Permission denied` on Secret Manager**
Run: `gcloud auth application-default login`

**Cloud Run service shows `Error: failed to create containerd task`**
Usually a memory issue. The service is configured for 4 GiB which is sufficient, but if you're on the free tier and see OOM, the Cloud Run free tier does support 4 GiB — check that billing is enabled on your project.

**`/run_match` returns 504 (timeout)**
The default timeout is 270 seconds. If your dataset is large, the first cold-start run may take longer. Try running again — subsequent runs are faster because the model is already loaded in memory.
