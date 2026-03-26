# Deployment Runbook

This repo is configured so both Vercel frontends proxy `/api/*` to:

`https://ncsu-matching-api.onrender.com/api/$1`

## 1) Deploy Backend on Render

1. Push the latest code to GitHub.
2. In Render, create a **Blueprint** service from this repo.
3. Render will detect [render.yaml](/Users/kaylaradu/GitHubRepos/NLP_Matching/render.yaml) and create:
   - web service `ncsu-matching-api`
   - persistent disk mounted at `/var/data`
4. Wait until deploy is healthy, then verify:
   - `https://ncsu-matching-api.onrender.com/`
   - `https://ncsu-matching-api.onrender.com/api/stats`

## 2) Redeploy Frontends on Vercel

The Vercel configs already proxy to the Render backend:

- [flutter_mentee/vercel.json](/Users/kaylaradu/GitHubRepos/NLP_Matching/flutter_mentee/vercel.json)
- [flutter_mentor/vercel.json](/Users/kaylaradu/GitHubRepos/NLP_Matching/flutter_mentor/vercel.json)

Trigger redeploys for both projects in Vercel after merging these changes.

## 3) Verify Google Form Forwarding

Run the backend smoke test from this repo:

```bash
bash backend/scripts/smoke_submit_mentee.sh
```

Expected output includes:

- `success=true`
- `google_form.forwarded=true`

Then confirm a new response appears in Google Forms with the **single question** containing the full JSON payload.

## 4) Verify Through the Deployed Frontend

1. Submit from `https://menteeform.vercel.app`
2. Confirm success in UI.
3. Confirm backend accepted it:
   - `https://ncsu-matching-api.onrender.com/api/stats`
4. Confirm Google Form has a new row containing the full JSON in the test field (`entry.1048570048`).

## Notes

- Backend storage now supports deployment path overrides via `APP_STORAGE_DIR`.
- For Render, `APP_STORAGE_DIR=/var/data` is already set in [render.yaml](/Users/kaylaradu/GitHubRepos/NLP_Matching/render.yaml).
- Mentor Google Form forwarding is currently disabled by default.
