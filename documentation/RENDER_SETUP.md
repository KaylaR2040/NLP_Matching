# Render Deployment Setup (Backend)

The FastAPI backend is deployed on Render as a **Docker web service**. Render is used instead of Vercel because the NLP matching engine (`sentence-transformers`) requires loading a ~420 MB model — this exceeds Vercel's 60-second request timeout.

## 1. Create a Render Account

Go to [render.com](https://render.com) and sign up or log in.

## 2. Connect Your GitHub Repository

1. In the Render dashboard, click **New +** → **Web Service**
2. Click **Connect a repository**
3. Select your GitHub account and choose the `NLP_Matching` repo
4. Click **Connect**

## 3. Configure the Web Service

Fill in these fields:

| Field | Value |
|---|---|
| **Name** | `nlp-mentor-backend` (or any name) |
| **Region** | US East (or closest to your users) |
| **Branch** | `main` |
| **Runtime** | **Docker** |
| **Dockerfile Path** | `wrapper/backend/Dockerfile` |
| **Docker Context** | `wrapper/backend` |
| **Instance Type** | `Starter` ($7/mo, 512 MB RAM) — minimum viable. Upgrade to `Standard` (2 GB) if you see OOM crashes during `/run_match`. |
| **Health Check Path** | `/health` |

> **Root Directory confusion**: The Docker context is `wrapper/backend`, not the repo root. Render builds from `wrapper/backend/Dockerfile` and the context includes `wrapper/backend/nlp_project/` (already copied there by `prepare_vercel_bundle.py`).

## 4. Set Environment Variables

In the **Environment** section, add these key-value pairs. Do NOT put these in `render.yaml` — that file is checked into git.

### Required Secrets

| Key | Value | How to generate |
|---|---|---|
| `DATABASE_URL` | Neon connection string | Neon console → Connection Details |
| `WRAPPER_TOKEN_SECRET` | 64-char hex string | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `WRAPPER_USER_USERNAME` | e.g. `eceaccount` | Choose freely |
| `WRAPPER_USER_PASSWORD_HASH` | PBKDF2 hash | `python wrapper/backend/scripts/generate_password_hash.py` |
| `WRAPPER_DEV_USERNAME` | e.g. `devaccount` | Choose freely |
| `WRAPPER_DEV_PASSWORD_HASH` | PBKDF2 hash | Same script as above |

### Already in render.yaml (no need to set manually)

These are defined in `render.yaml` and will be applied automatically:
- `WRAPPER_MENTOR_STORAGE_MODE=postgres`
- `WRAPPER_NLP_PROJECT_DIR=/app/nlp_project`
- `WRAPPER_REQUIRE_HTTPS=true`
- `WRAPPER_MATCH_TIMEOUT_SECONDS=270`
- `WRAPPER_SCRIPT_TIMEOUT_SECONDS=180`
- `WRAPPER_ALLOWED_ORIGINS=https://mentorform.vercel.app,https://menteeform.vercel.app,https://matching-web-ten.vercel.app`

> Update `WRAPPER_ALLOWED_ORIGINS` if your Flutter frontend URLs differ.

## 5. Deploy

Click **Create Web Service**. The first build will take **10–20 minutes** because:
- `torch` (~2 GB) must be downloaded and installed
- `sentence-transformers` model (`all-mpnet-base-v2`, ~420 MB) is pre-downloaded during the build

Subsequent deploys reuse Docker layer caches and are much faster (~3–5 min).

## 6. Verify the Deployment

Once the dashboard shows **Live**:

```bash
curl https://YOUR-SERVICE.onrender.com/health
# → {"status": "ok", "service": "NLP Mentor Matcher Wrapper API", ...}

curl https://YOUR-SERVICE.onrender.com/config/orgs | head -c 100
# → ["1911 Consulting","Acappology",...]
```

## 7. Note Your Backend URL

Copy the Render service URL (e.g., `https://nlp-mentor-backend.onrender.com`). You will need it for:
- `WRAPPER_API_BASE_URL` in the Vercel admin frontend project
- `BACKEND_CONFIG_URL` in Vercel flutter_mentor and flutter_mentee build settings
- `WRAPPER_ALLOWED_ORIGINS` in your Render environment variables

## 8. After Deployment: Run DB Setup

If you haven't already initialized the Neon schema:

```bash
# From your local machine, with DATABASE_URL set
python wrapper/backend/scripts/init_schema.py
python wrapper/backend/scripts/seed_config_lists.py
```

Or trigger via the admin UI's Dev Dashboard after logging in.

## 9. Redeploy

Push to your `main` branch — Render auto-deploys on every push if **Auto-Deploy** is enabled (it is by default).

To redeploy manually: Render dashboard → your service → **Manual Deploy** → **Deploy latest commit**.

## 10. View Logs

Render dashboard → your service → **Logs** tab.

Filter by text (e.g., `run_match`, `cors`, `ERROR`) using the log search box.

For structured backend logs, look for lines starting with the timestamp format used by Python `logging`.

## 11. Free Tier Limitation

On the free tier, Render **spins down** the service after 15 minutes of inactivity and **spins back up** on the next request (30–60 second cold start). The model is already in the Docker image so the cold start is just container startup, not a re-download.

Upgrade to the `Starter` ($7/mo) plan to avoid spin-downs.

## 12. Updating nlp_project in the Docker Image

If you edit `nlp_project/` source files, you must re-sync them into `wrapper/backend/nlp_project/` before pushing:

```bash
python wrapper/backend/scripts/prepare_vercel_bundle.py
git add wrapper/backend/nlp_project/
git commit -m "sync nlp_project bundle"
git push
```

Render will then rebuild the Docker image with the updated code.
