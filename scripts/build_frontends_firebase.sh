#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -z "${BACKEND_API_BASE_URL:-}" ]]; then
  echo "ERROR: BACKEND_API_BASE_URL is required (example: https://api.example.com)." >&2
  exit 1
fi

# Admin wrapper keeps its existing WRAPPER_API_BASE_URL contract.
WRAPPER_API_BASE_URL="${WRAPPER_API_BASE_URL:-$BACKEND_API_BASE_URL}"

FLUTTER_SDK_DIR="${FLUTTER_SDK_DIR:-$ROOT_DIR/.flutter_sdk}"
if [[ ! -x "$FLUTTER_SDK_DIR/bin/flutter" ]]; then
  git clone --depth 1 --branch stable https://github.com/flutter/flutter.git "$FLUTTER_SDK_DIR"
fi

export PATH="$FLUTTER_SDK_DIR/bin:$PATH"
flutter config --enable-web >/dev/null

build_flutter_web() {
  local project_dir="$1"
  local define_key="$2"
  local define_value="$3"

  echo "Building $project_dir with $define_key=$define_value"
  pushd "$project_dir" >/dev/null
  flutter pub get
  flutter build web --release --dart-define="${define_key}=${define_value}"
  popd >/dev/null
}

build_flutter_web "wrapper/flutter_wrapper" "WRAPPER_API_BASE_URL" "$WRAPPER_API_BASE_URL"
build_flutter_web "flutter_mentor" "BACKEND_API_BASE_URL" "$BACKEND_API_BASE_URL"
build_flutter_web "flutter_mentee" "BACKEND_API_BASE_URL" "$BACKEND_API_BASE_URL"

echo "Firebase web build artifacts are ready."
