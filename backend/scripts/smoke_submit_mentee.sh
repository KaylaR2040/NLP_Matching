#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${1:-https://ncsu-matching-api.onrender.com/api}"

payload='{
  "email": "smoke.test+ncsu@example.com",
  "firstName": "Smoke",
  "lastName": "Test",
  "pronouns": "she/her",
  "educationLevel": "BS",
  "graduationSemester": "Spring",
  "graduationYear": "2027",
  "degreePrograms": ["Computer Engineering"],
  "previousMentorship": false,
  "studentOrgs": ["Institute of Electrical and Electronics Engineers"],
  "experienceLevel": "Beginner",
  "industriesOfInterest": ["Software Engineering"],
  "aboutYourself": "Automated end-to-end submission smoke test",
  "matchByIndustry": 4.0,
  "matchByDegree": 3.0,
  "matchByClubs": 2.0,
  "matchByIdentity": 1.0,
  "matchByGradYears": 2.0,
  "helpTopics": ["Internships"]
}'

echo "Posting sample mentee payload to ${API_BASE_URL}/mentees/"
response="$(curl -sS -X POST "${API_BASE_URL}/mentees/" \
  -H "Content-Type: application/json" \
  -d "${payload}")"

echo "Raw response:"
echo "${response}"

echo
echo "Forwarding status:"
python3 - <<'PY' "${response}"
import json
import sys

resp = json.loads(sys.argv[1])
google = resp.get("google_form", {})
print(f"success={resp.get('success')}")
print(f"google_form.forwarded={google.get('forwarded')}")
print(f"google_form.skipped={google.get('skipped')}")
print(f"google_form.status_code={google.get('status_code')}")
print(f"google_form.reason={google.get('reason')}")
PY
