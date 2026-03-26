# Deployment Runbook

## Current Production Path (No Separate Backend Required)

This repo now includes Vercel serverless endpoints inside each frontend project:

- `flutter_mentee/api/mentees.js`
- `flutter_mentor/api/mentors.js`

These endpoints receive the submitted JSON and forward it to Google Forms.

### What to deploy

1. Push this code to GitHub.
2. Redeploy:
   - `menteeform.vercel.app` (project root: `flutter_mentee`)
   - `mentorform.vercel.app` (project root: `flutter_mentor`)

### Verify mentee submission

1. Open `https://menteeform.vercel.app`
2. Submit the mentee form.
3. Confirm the response is successful.
4. Check Google Form responses:
   - the one test field should contain the entire JSON payload.

The default mentee target is:

- `formResponse`: `https://docs.google.com/forms/d/e/1FAIpQLSes-SnnWAMcXzU_CsX6opYIpKxGu3Ii1BqfhMDUfN9IV4-pqQ/formResponse`
- entry id: `entry.1048570048`

### Optional env vars (Vercel project settings)

- `MENTEE_GOOGLE_FORM_ENABLED` (`true` / `false`)
- `MENTEE_GOOGLE_FORM_REQUIRED` (`true` / `false`)
- `MENTEE_GOOGLE_FORM_RESPONSE_URL`
- `MENTEE_GOOGLE_FORM_JSON_ENTRY_ID`
- `MENTEE_GOOGLE_FORM_FIELD_MAP_JSON` (JSON object for future field-level mapping)

Mentor equivalents are also supported:

- `MENTOR_GOOGLE_FORM_ENABLED`
- `MENTOR_GOOGLE_FORM_REQUIRED`
- `MENTOR_GOOGLE_FORM_RESPONSE_URL`
- `MENTOR_GOOGLE_FORM_JSON_ENTRY_ID`
- `MENTOR_GOOGLE_FORM_FIELD_MAP_JSON`

## Optional Full Backend Mode (Render)

If you want persistent JSON storage + NLP matching endpoints, deploy `backend/` on Render via [render.yaml](/Users/kaylaradu/GitHubRepos/NLP_Matching/render.yaml). This is optional for the Google Form forwarding test.
