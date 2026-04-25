# Deployment Guide

Complete step-by-step guide to deploying the full system from scratch.

**Stack:** Google Cloud Run (backend) + Firebase Hosting (frontends) + Neon Postgres (database)

**Cost:** Free tier covers normal usage for a low-traffic academic program.

---

## Overview

| Step | What | Where |
|---|---|---|
| 1 | Install tools | Your Mac |
| 2 | Create GCP project + enable APIs | Google Cloud |
| 3 | Store secrets | Google Secret Manager |
| 4 | Deploy backend | Google Cloud Run |
| 5 | Initialize database | Neon (runs from your Mac) |
| 6 | Deploy frontends | Firebase Hosting |
| 7 | Update CORS + redeploy backend | Google Cloud Run |
| 8 | Test everything | curl + browser |

---

## Step 1 — Install Tools (once)

```bash
# Google Cloud CLI
brew install --cask google-cloud-sdk

# Firebase CLI (requires Node.js — install from nodejs.org if needed)
npm install -g firebase-tools

# Docker Desktop — download from https://www.docker.com/products/docker-desktop
# Start Docker Desktop before continuing.

# Log in
gcloud auth login
gcloud auth application-default login
```

---

## Step 2 — Create GCP Project + Enable APIs

```bash
# Pick a project ID (lowercase, hyphens only, e.g. nlp-mentor-2026)
export PROJECT_ID=nlp-mentor-2026

# Create the project
gcloud projects create $PROJECT_ID --name="NLP Mentor Matching"

# Set it as the active project
gcloud config set project $PROJECT_ID

# Enable required APIs (takes about 2 minutes)
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com

# Configure Docker to push to Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
```

> **Billing note:** You must enable billing on the project for Cloud Run and Artifact Registry to work, even on the free tier. Go to console.cloud.google.com → Billing → Link a billing account. You will not be charged for normal usage within free tier limits.

---

## Step 3 — Store Secrets in Secret Manager

Your secrets live in `wrapper/backend/.env`. The helper script reads that file and stores the sensitive values in Google Secret Manager (so they're never in your code or Docker image).

```bash
cd /path/to/NLP_Matching

PROJECT_ID=$PROJECT_ID ./scripts/upsert_cloud_run_secrets.sh wrapper/backend/.env
```

This stores 6 secrets:
- `DATABASE_URL` — your Neon connection string
- `WRAPPER_TOKEN_SECRET` — auth token signing key
- `WRAPPER_USER_USERNAME` / `WRAPPER_USER_PASSWORD_HASH`
- `WRAPPER_DEV_USERNAME` / `WRAPPER_DEV_PASSWORD_HASH`

To verify they were created:
```bash
gcloud secrets list --project $PROJECT_ID
```

---

## Step 4 — Deploy Backend to Cloud Run

For the first deploy, use placeholder CORS origins — you'll get the real Firebase URLs in Step 6.

```bash
export PROJECT_ID=$PROJECT_ID
export WRAPPER_ALLOWED_ORIGINS="https://placeholder.web.app"

./scripts/deploy_backend_cloud_run.sh
```

**First build takes 15–20 minutes** because Docker downloads PyTorch (~2 GB) and the sentence-transformers model (~420 MB) and bakes them into the image. Subsequent deploys reuse cached layers and take ~3 minutes.

When it finishes, the script prints:
```
Cloud Run deployment complete.
Service URL: https://nlp-mentor-backend-XXXXXXXX-uc.a.run.app
```

**Copy and save this URL.** You need it for Steps 5 and 6.

Quick verify:
```bash
export BACKEND=https://nlp-mentor-backend-XXXXXXXX-uc.a.run.app

curl $BACKEND/health
# → {"status":"ok","service":"NLP Mentor Matcher Wrapper API"}
```

---

## Step 5 — Initialize Neon Database

Your `DATABASE_URL` is already in `wrapper/backend/.env`. Run the schema and seed scripts from your Mac:

```bash
cd /path/to/NLP_Matching

# Activate your Python virtual environment
source wrapper/backend/.venv/bin/activate
# (or: python -m venv wrapper/backend/.venv && pip install -r wrapper/backend/requirements.txt)

# Create tables
python wrapper/backend/scripts/init_schema.py

# Load config lists from data/*.txt files into Neon
python wrapper/backend/scripts/seed_config_lists.py
```

Verify the seed worked via Cloud Run:
```bash
curl $BACKEND/config/orgs | head -c 120
# → ["1911 Consulting","Acappology","Accounting Society",...]
```

---

## Step 6 — Deploy Frontends to Firebase Hosting

See the full guide: [FIREBASE_SETUP.md](FIREBASE_SETUP.md)

Short version:

```bash
# Log in to Firebase
firebase login

# Link Firebase to your GCP project
firebase projects:addfirebase $PROJECT_ID

# Create 3 hosting sites in Firebase Console:
# console.firebase.google.com → your project → Hosting → Add another site
# Example site IDs: nlp-admin, nlp-mentor, nlp-mentee

# Wire up the targets
./scripts/firebase_apply_targets.sh $PROJECT_ID nlp-admin nlp-mentor nlp-mentee

# Build and deploy all 3 Flutter apps
export WRAPPER_API_BASE_URL=$BACKEND
export BACKEND_API_BASE_URL=$BACKEND
export FIREBASE_PROJECT_ID=$PROJECT_ID
./scripts/deploy_frontends_firebase.sh
```

After deploy you get URLs like:
- Admin: `https://nlp-admin.web.app`
- Mentor form: `https://nlp-mentor.web.app`
- Mentee form: `https://nlp-mentee.web.app`

---

## Step 7 — Update CORS + Redeploy Backend

Now that you have real frontend URLs, redeploy the backend with the correct CORS origins:

```bash
export PROJECT_ID=$PROJECT_ID
export WRAPPER_ALLOWED_ORIGINS="https://nlp-admin.web.app,https://nlp-mentor.web.app,https://nlp-mentee.web.app"

./scripts/deploy_backend_cloud_run.sh
```

This redeploy is fast (~3 min) because Docker layers are cached.

---

## Step 8 — End-to-End Test

```bash
BACKEND=https://YOUR-CLOUD-RUN-URL

# 1. Health
curl $BACKEND/health

# 2. Config lists
curl $BACKEND/config/orgs | head -c 100
curl $BACKEND/config/concentrations | head -c 100

# 3. Login
TOKEN=$(curl -s -X POST $BACKEND/login \
  -H "Content-Type: application/json" \
  -d '{"username":"devaccount","password":"YOUR-PASSWORD"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
echo "Token: $TOKEN"

# 4. List mentors
curl -H "Authorization: Bearer $TOKEN" $BACKEND/mentors
```

In your browser:
- Open `https://nlp-admin.web.app` → should show login page → log in → works
- Open `https://nlp-mentor.web.app` → org dropdowns should load from backend
- Open `https://nlp-mentee.web.app` → concentration dropdown should load from backend

---

## Redeploying After Code Changes

**Backend changes:**
```bash
git push  # if you have Cloud Build auto-deploy set up
# OR manually:
export PROJECT_ID=nlp-mentor-2026
export WRAPPER_ALLOWED_ORIGINS="https://nlp-admin.web.app,https://nlp-mentor.web.app,https://nlp-mentee.web.app"
./scripts/deploy_backend_cloud_run.sh
```

**Frontend changes:**
```bash
export WRAPPER_API_BASE_URL=$BACKEND
export BACKEND_API_BASE_URL=$BACKEND
export FIREBASE_PROJECT_ID=$PROJECT_ID
./scripts/deploy_frontends_firebase.sh
```

**nlp_project changes** (matching logic): changes are picked up automatically since `nlp_project/` is copied from the repo root at Docker build time — no extra steps needed.
