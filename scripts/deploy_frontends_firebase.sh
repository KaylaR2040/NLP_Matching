#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v firebase >/dev/null 2>&1; then
  echo "ERROR: firebase CLI not found. Install with: npm i -g firebase-tools" >&2
  exit 1
fi

"$ROOT_DIR/scripts/build_frontends_firebase.sh"

FIREBASE_PROJECT_ID="${FIREBASE_PROJECT_ID:-}"
DEPLOY_ARGS=(
  deploy
  --only hosting:admin,hosting:mentor,hosting:mentee
  --non-interactive
)

if [[ -n "$FIREBASE_PROJECT_ID" ]]; then
  DEPLOY_ARGS+=(--project "$FIREBASE_PROJECT_ID")
fi

if [[ -n "${FIREBASE_TOKEN:-}" ]]; then
  DEPLOY_ARGS+=(--token "$FIREBASE_TOKEN")
fi

firebase "${DEPLOY_ARGS[@]}"

echo "Firebase frontend deployment complete."
