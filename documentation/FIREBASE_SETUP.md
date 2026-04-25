# Firebase Hosting Setup (Frontends)

Three Flutter Web apps are deployed to Firebase Hosting:

| App | Folder | Purpose |
|---|---|---|
| Admin UI | `wrapper/flutter_wrapper` | Login, matching, mentor management |
| Mentor registration | `flutter_mentor` | Public mentor signup form |
| Mentee registration | `flutter_mentee` | Public mentee signup form |

For the full ordered setup (do this after Cloud Run), see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

---

## Prerequisites

- Node.js installed (`brew install node`)
- Firebase CLI installed: `npm install -g firebase-tools`
- Flutter SDK installed (`brew install --cask flutter` or from flutter.dev)
- Cloud Run backend already deployed (you need the backend URL)

---

## Step 1 — Log in to Firebase

```bash
firebase login
```

---

## Step 2 — Link Firebase to Your GCP Project

```bash
# Use the same project ID as Cloud Run
firebase projects:addfirebase YOUR-GCP-PROJECT-ID
```

If prompted, select your GCP project from the list.

---

## Step 3 — Create 3 Hosting Sites

Each Flutter app gets its own Firebase Hosting site with a separate `.web.app` URL.

**In the Firebase Console:**
1. Go to [console.firebase.google.com](https://console.firebase.google.com)
2. Select your project
3. In the left sidebar: **Hosting**
4. Click **Add another site** (you'll do this twice after the first default site)
5. Create sites with IDs like:
   - `nlp-admin` → becomes `https://nlp-admin.web.app`
   - `nlp-mentor` → becomes `https://nlp-mentor.web.app`
   - `nlp-mentee` → becomes `https://nlp-mentee.web.app`

> Site IDs must be globally unique across all Firebase projects. If `nlp-admin` is taken, try `ecementor-admin` or similar.

---

## Step 4 — Wire Up Hosting Targets

Run this script to map target names (`admin`, `mentor`, `mentee`) to your site IDs:

```bash
./scripts/firebase_apply_targets.sh \
  YOUR-GCP-PROJECT-ID \
  nlp-admin \
  nlp-mentor \
  nlp-mentee
```

This updates `.firebaserc` with the target mappings used by `firebase.json`.

---

## Step 5 — Build and Deploy All 3 Apps

```bash
export BACKEND_API_BASE_URL=https://YOUR-CLOUD-RUN-URL.a.run.app
export WRAPPER_API_BASE_URL=https://YOUR-CLOUD-RUN-URL.a.run.app
export FIREBASE_PROJECT_ID=YOUR-GCP-PROJECT-ID

./scripts/deploy_frontends_firebase.sh
```

What this does:
1. Clones Flutter SDK if not present
2. Builds `wrapper/flutter_wrapper` with `--dart-define=WRAPPER_API_BASE_URL=$WRAPPER_API_BASE_URL`
3. Builds `flutter_mentor` with `--dart-define=BACKEND_API_BASE_URL=$BACKEND_API_BASE_URL`
4. Builds `flutter_mentee` with `--dart-define=BACKEND_API_BASE_URL=$BACKEND_API_BASE_URL`
5. Runs `firebase deploy --only hosting` for all three targets

After deploy, Firebase prints the live URLs:
```
✔  Deploy complete!

Project Console: https://console.firebase.google.com/project/YOUR-PROJECT/overview
Hosting URL (admin):  https://nlp-admin.web.app
Hosting URL (mentor): https://nlp-mentor.web.app
Hosting URL (mentee): https://nlp-mentee.web.app
```

**Save these URLs** — you need them for Step 6 (CORS update on Cloud Run).

---

## Step 6 — Update CORS on the Backend

Go back to Cloud Run and redeploy with the real frontend URLs as allowed origins:

```bash
export PROJECT_ID=YOUR-GCP-PROJECT-ID
export WRAPPER_ALLOWED_ORIGINS="https://nlp-admin.web.app,https://nlp-mentor.web.app,https://nlp-mentee.web.app"
./scripts/deploy_backend_cloud_run.sh
```

This redeploy is fast (~3 min) — Docker layers are cached from the first build.

---

## Verify

Open each URL in a browser:

- `https://nlp-admin.web.app` → should show login screen → log in with your dev credentials → dashboard loads
- `https://nlp-mentor.web.app` → should show mentor registration form → org dropdown should populate from backend
- `https://nlp-mentee.web.app` → should show mentee registration form → concentration dropdown should populate

Test CORS from command line:
```bash
curl -H "Origin: https://nlp-mentor.web.app" \
  -I https://YOUR-CLOUD-RUN-URL.a.run.app/config/orgs
# Look for: access-control-allow-origin: https://nlp-mentor.web.app
```

---

## Redeploying After Changes

```bash
export BACKEND_API_BASE_URL=https://YOUR-CLOUD-RUN-URL.a.run.app
export WRAPPER_API_BASE_URL=https://YOUR-CLOUD-RUN-URL.a.run.app
export FIREBASE_PROJECT_ID=YOUR-GCP-PROJECT-ID
./scripts/deploy_frontends_firebase.sh
```

---

## Auto-Deploy on Push (optional)

Set up a Cloud Build trigger for automatic frontend deploys:

1. Cloud Console → Cloud Build → Triggers → Create Trigger
2. Source: your GitHub repo, branch `main`
3. Build config: `cloudbuild.frontends.yaml`
4. Add substitutions:
   - `_FIREBASE_PROJECT_ID` = your project ID
   - `_WRAPPER_API_BASE_URL` = your Cloud Run URL
   - `_BACKEND_API_BASE_URL` = your Cloud Run URL
5. Create a Secret Manager secret `FIREBASE_CI_TOKEN`:
   ```bash
   firebase login:ci   # prints a CI token
   echo "YOUR-CI-TOKEN" | gcloud secrets create FIREBASE_CI_TOKEN --data-file=-
   ```

---

## Troubleshooting

**`firebase: command not found`**
Run: `npm install -g firebase-tools`

**`Error: Hosting site not found`**
Run `firebase_apply_targets.sh` again with the correct site IDs. Site IDs must exactly match what you created in the Firebase Console.

**Build fails: `flutter: command not found`**
The `build_frontends_firebase.sh` script clones Flutter into the repo if not found. Make sure you have git installed and enough disk space (~2 GB for Flutter + dependencies).

**Org/concentration dropdowns empty in mentor/mentee apps**
- Check that `BACKEND_API_BASE_URL` was set correctly when building
- Test: `curl https://YOUR-CLOUD-RUN-URL.a.run.app/config/orgs` — should return a list
- If list is empty, run the Neon seed script: `python wrapper/backend/scripts/seed_config_lists.py`

**CORS error when mentor form submits**
- `WRAPPER_ALLOWED_ORIGINS` on Cloud Run must include `https://nlp-mentor.web.app` exactly (no trailing slash)
- Redeploy backend with correct CORS after getting real Firebase URLs

**White screen / 404 after page refresh**
This is normal for Flutter web with path routing. The `firebase.json` already includes SPA rewrites (`"source": "/**", "destination": "/index.html"`) for all three targets — this should not happen. If it does, verify the `firebase.json` rewrites are present.
