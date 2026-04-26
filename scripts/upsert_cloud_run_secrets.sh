#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "ERROR: gcloud CLI is required." >&2
  exit 1
fi

ENV_FILE="${1:-wrapper/backend/.env}"
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: Set PROJECT_ID or run: gcloud config set project <id>" >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi

SECRET_KEYS=(
  DATABASE_URL
  WRAPPER_TOKEN_SECRET
  WRAPPER_USER_USERNAME
  WRAPPER_USER_PASSWORD_HASH
  WRAPPER_DEV_USERNAME
  WRAPPER_DEV_PASSWORD_HASH
)

for key in "${SECRET_KEYS[@]}"; do
  raw_line="$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 || true)"
  value="${raw_line#${key}=}"
  if [[ -z "$raw_line" || -z "$value" ]]; then
    echo "Skipping $key (missing from $ENV_FILE)"
    continue
  fi

  if ! gcloud secrets describe "$key" --project "$PROJECT_ID" >/dev/null 2>&1; then
    gcloud secrets create "$key" --replication-policy=automatic --project "$PROJECT_ID"
  fi

  printf '%s' "$value" | gcloud secrets versions add "$key" --data-file=- --project "$PROJECT_ID" >/dev/null
  echo "Updated secret: $key"
done

echo "Secret sync complete for project: $PROJECT_ID"
