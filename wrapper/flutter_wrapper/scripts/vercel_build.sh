#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -z "${WRAPPER_API_BASE_URL:-}" ]]; then
  echo "ERROR: WRAPPER_API_BASE_URL is required for frontend build."
  exit 1
fi

FLUTTER_SDK_DIR="${FLUTTER_SDK_DIR:-$ROOT_DIR/.flutter_sdk}"

if [[ ! -x "$FLUTTER_SDK_DIR/bin/flutter" ]]; then
  git clone --depth 1 --branch stable https://github.com/flutter/flutter.git "$FLUTTER_SDK_DIR"
fi

export PATH="$FLUTTER_SDK_DIR/bin:$PATH"
flutter config --enable-web
flutter pub get
flutter build web --release --dart-define=WRAPPER_API_BASE_URL="$WRAPPER_API_BASE_URL"
