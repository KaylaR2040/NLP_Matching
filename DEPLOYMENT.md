# Deployment Runbook

This project now uses Vercel serverless API routes as the backend for Google Form submission:

- `flutter_mentee/api/mentees.js`
- `flutter_mentor/api/mentors.js`

## Deploy

1. Push this repo.
2. Redeploy `menteeform.vercel.app` (root: `flutter_mentee`).
3. Redeploy `mentorform.vercel.app` (root: `flutter_mentor`).

## Change Google Form Later (Simple Path)

You only need to edit two things per app:

- `*_PREFILLED_LINK` in form definition file
- `*_FIELD_ORDER` in the same file (must match query param order in your prefilled link)

Files:

- mentee: [flutter_mentee/api/_lib/mentee_form_definition.js](/Users/kaylaradu/GitHubRepos/NLP_Matching/flutter_mentee/api/_lib/mentee_form_definition.js)
- mentor: [flutter_mentor/api/_lib/mentor_form_definition.js](/Users/kaylaradu/GitHubRepos/NLP_Matching/flutter_mentor/api/_lib/mentor_form_definition.js)

The API auto-converts `.../viewform?...` to `.../formResponse` and auto-builds `entry.*` mapping from the link.

## Optional Env Overrides (Vercel)

Mentee:

- `MENTEE_GOOGLE_FORM_ENABLED`
- `MENTEE_GOOGLE_FORM_REQUIRED`
- `MENTEE_GOOGLE_FORM_PREFILLED_LINK`
- `MENTEE_GOOGLE_FORM_RESPONSE_URL`
- `MENTEE_GOOGLE_FORM_FIELD_MAP_JSON`
- `MENTEE_GOOGLE_FORM_JSON_ENTRY_ID`

Mentor:

- `MENTOR_GOOGLE_FORM_ENABLED`
- `MENTOR_GOOGLE_FORM_REQUIRED`
- `MENTOR_GOOGLE_FORM_PREFILLED_LINK`
- `MENTOR_GOOGLE_FORM_RESPONSE_URL`
- `MENTOR_GOOGLE_FORM_FIELD_MAP_JSON`
- `MENTOR_GOOGLE_FORM_JSON_ENTRY_ID`
