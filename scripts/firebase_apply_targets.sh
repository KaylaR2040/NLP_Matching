#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "Usage: $0 <firebase-project-id> <admin-site-id> <mentor-site-id> <mentee-site-id>" >&2
  exit 1
fi

PROJECT_ID="$1"
ADMIN_SITE_ID="$2"
MENTOR_SITE_ID="$3"
MENTEE_SITE_ID="$4"

firebase use "$PROJECT_ID"
firebase target:apply hosting admin "$ADMIN_SITE_ID"
firebase target:apply hosting mentor "$MENTOR_SITE_ID"
firebase target:apply hosting mentee "$MENTEE_SITE_ID"

echo "Firebase hosting targets configured for project: $PROJECT_ID"
