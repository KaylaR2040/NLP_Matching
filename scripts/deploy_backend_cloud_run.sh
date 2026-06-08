#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "ERROR: gcloud CLI is required." >&2
  exit 1
fi
# Docker is not required — we build remotely on Cloud Build.

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: Set PROJECT_ID or run: gcloud config set project <id>" >&2
  exit 1
fi

REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-nlp-mentor-backend}"
ARTIFACT_REPO="${ARTIFACT_REPO:-cloud-run-images}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"
IMAGE_URI="${IMAGE_URI:-${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/${SERVICE_NAME}:${IMAGE_TAG}}"

DEFAULT_ALLOWED_ORIGINS="https://admin.example.com,https://mentor.example.com,https://mentee.example.com"
ALLOWED_ORIGINS="${WRAPPER_ALLOWED_ORIGINS:-$DEFAULT_ALLOWED_ORIGINS}"

# Use a custom delimiter (##) so comma-separated origins are preserved.
NOTIFY_EMAIL="${FORM_NOTIFICATION_TO_EMAIL:-kngodfre@ncsu.edu}"
NON_SECRET_ENV_VARS="${NON_SECRET_ENV_VARS:-^##^WRAPPER_MENTOR_STORAGE_MODE=postgres##WRAPPER_NLP_PROJECT_DIR=/app/nlp_project##WRAPPER_MATCH_TIMEOUT_SECONDS=270##WRAPPER_SCRIPT_TIMEOUT_SECONDS=180##WRAPPER_REQUIRE_HTTPS=true##WRAPPER_ALLOWED_ORIGINS=${ALLOWED_ORIGINS}##FORM_NOTIFICATION_TO_EMAIL=${NOTIFY_EMAIL}}"

# Sensitive values come from Secret Manager, injected into the Cloud Run revision.
SECRET_ENV_VARS="${SECRET_ENV_VARS:-DATABASE_URL=DATABASE_URL:latest,WRAPPER_TOKEN_SECRET=WRAPPER_TOKEN_SECRET:latest,WRAPPER_USER_USERNAME=WRAPPER_USER_USERNAME:latest,WRAPPER_USER_PASSWORD_HASH=WRAPPER_USER_PASSWORD_HASH:latest,WRAPPER_DEV_USERNAME=WRAPPER_DEV_USERNAME:latest,WRAPPER_DEV_PASSWORD_HASH=WRAPPER_DEV_PASSWORD_HASH:latest,SMTP_USER=SMTP_USER:latest,SMTP_PASSWORD=SMTP_PASSWORD:latest}"

echo "Using PROJECT_ID=${PROJECT_ID} REGION=${REGION} SERVICE_NAME=${SERVICE_NAME}"
echo "Ensuring Artifact Registry repository '${ARTIFACT_REPO}' exists..."
if ! gcloud artifacts repositories describe "$ARTIFACT_REPO" \
  --location "$REGION" \
  --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$ARTIFACT_REPO" \
    --repository-format docker \
    --location "$REGION" \
    --description "Container images for Cloud Run deployments" \
    --project "$PROJECT_ID"
fi

# Build on Cloud Build (remote — no local Docker memory limit, free 120 min/day).
# Uploads repo source to Cloud Storage, builds with wrapper/backend/Dockerfile,
# and pushes the resulting image directly to Artifact Registry.
echo "Building backend image on Cloud Build: ${IMAGE_URI}"
gcloud builds submit \
  --project "$PROJECT_ID" \
  --config cloudbuild.image.yaml \
  --substitutions="_IMAGE_URI=${IMAGE_URI}" \
  --timeout=1800 \
  .

echo "Deploying Cloud Run service..."
DEPLOY_ARGS=(
  run deploy "$SERVICE_NAME"
  --project "$PROJECT_ID"
  --region "$REGION"
  --platform managed
  --image "$IMAGE_URI"
  --allow-unauthenticated
  --ingress all
  --cpu 1
  --memory 4Gi
  --concurrency 1
  --timeout 300
  --min-instances 0
  --max-instances 3
  --set-env-vars "$NON_SECRET_ENV_VARS"
)

if [[ -n "$SECRET_ENV_VARS" ]]; then
  DEPLOY_ARGS+=(--set-secrets "$SECRET_ENV_VARS")
fi

gcloud "${DEPLOY_ARGS[@]}"

echo "Cloud Run deployment complete."
echo "Service URL: $(gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" --format='value(status.url)')"
