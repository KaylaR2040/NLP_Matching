# Troubleshooting

## Render / Backend

### Service shows "Failed" or never goes Live

**Check build logs** (Render dashboard → service → Logs → Build):

- `No module named 'torch'` → `torch` missing from `requirements.txt`. Confirm line `torch>=2.2.0` exists.
- `Dockerfile not found` → Check **Dockerfile Path** is `wrapper/backend/Dockerfile` and **Docker Context** is `wrapper/backend`.
- `nlp_project/main.py not found` → `wrapper/backend/nlp_project/` is missing. Run `python wrapper/backend/scripts/prepare_vercel_bundle.py` locally, commit, and push.
- Build times out → First build with `torch` takes 10–20 min. This is normal.

### GET /health returns 502 or no response

The container is still starting. Wait 2–3 minutes after deploy. If it persists:
- Check Logs for Python import errors or `ADDRESS ALREADY IN USE`
- Confirm `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]` in Dockerfile

### /run_match times out

- `WRAPPER_MATCH_TIMEOUT_SECONDS` is set too low. On Render, set it to `270`.
- The Starter plan (512 MB RAM) may OOM when loading torch + sentence-transformers + running inference. Upgrade to Standard (2 GB).
- Check logs for `MemoryError` or `Killed`.

### /run_match returns "nlp_project not found"

- `WRAPPER_NLP_PROJECT_DIR` env var is missing or wrong. Should be `/app/nlp_project`.
- `wrapper/backend/nlp_project/` may be missing. Check the repo and re-run `prepare_vercel_bundle.py`.

---

## Neon / Database

### Connection refused or SSL error

Neon connection strings must include `?sslmode=require`. Example:
```
postgresql://user:pass@host/dbname?sslmode=require
```

Check that `DATABASE_URL` doesn't have extra quotes or newlines in the Render dashboard.

### Tables don't exist

Run the schema init script:
```bash
python wrapper/backend/scripts/init_schema.py --database-url "$DATABASE_URL"
```

### Config lists return `[]`

Run the seed script:
```bash
python wrapper/backend/scripts/seed_config_lists.py --database-url "$DATABASE_URL"
```

Then verify:
```sql
SELECT list_key, length(content) FROM config_lists;
```

### Mentors not persisting across restarts

Make sure `WRAPPER_MENTOR_STORAGE_MODE=postgres` is set in Render. File mode writes to the container filesystem, which is ephemeral.

---

## CORS Errors

CORS errors appear as browser console messages like:
> `Access to fetch at 'https://...' from origin 'https://...' has been blocked by CORS policy`

**Fix:**
1. Check `WRAPPER_ALLOWED_ORIGINS` in your Render environment variables
2. It must include the exact origin of the Flutter app (no trailing slash):
   ```
   https://mentorform.vercel.app,https://menteeform.vercel.app,https://matching-web-ten.vercel.app
   ```
3. Redeploy the Render service after changing the env var
4. Test with curl:
   ```bash
   curl -H "Origin: https://mentorform.vercel.app" \
        -I https://YOUR-SERVICE.onrender.com/config/orgs
   # Should see: access-control-allow-origin: https://mentorform.vercel.app
   ```

---

## Flutter Apps

### Config lists show fallback values (not from backend)

flutter_mentor and flutter_mentee try the backend first, then fall back to asset files. If you see stale data:

1. Check `BACKEND_CONFIG_URL` is set in Vercel build settings and points to the correct Render URL (no trailing slash).
2. Open browser DevTools → Network → filter by `/config/` — you should see 200 responses.
3. If requests fail with CORS errors, fix CORS (see above).
4. If requests fail with 404, check the Render URL is correct and the service is running.

### Admin UI login fails

- Check `WRAPPER_USER_USERNAME`, `WRAPPER_USER_PASSWORD_HASH`, `WRAPPER_DEV_USERNAME`, `WRAPPER_DEV_PASSWORD_HASH` are set in Render.
- Hashes must be in PBKDF2 format. Generate with:
  ```bash
  python wrapper/backend/scripts/generate_password_hash.py --password "yourpassword"
  ```
- Check `WRAPPER_API_BASE_URL` in the Vercel admin frontend project points to Render.

### Admin UI shows "Session expired" immediately

`WRAPPER_TOKEN_SECRET` is not set or changed. Without a stable secret, tokens are invalidated on every container restart. Set `WRAPPER_TOKEN_SECRET` to a stable 64-char hex string in Render.

### Flutter web app returns 404 after page refresh

Flutter web with `PathUrlStrategy` needs a rewrite rule. Add a `vercel.json` to the Flutter project root:
```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

Or switch to `HashUrlStrategy` in `main.dart` (uses `#` in URLs, no server config needed).

---

## Excel / CSV Parsing

### /run_match returns "Required columns missing"

The mentee CSV must have at minimum these columns (or their aliases):
- `mentee_id` (or `id` or `email`)
- `mentee_name` (or `name`)

Check `nlp_project/mentor_matching/parsing.py` for the full list of column aliases.

### Uploaded XLSX fails to parse

- Make sure the file is a real XLSX (not a renamed CSV).
- `openpyxl` is required for XLSX. It's in `requirements.txt` — confirm it's installed.
- Try exporting as CSV first to isolate parsing issues.

---

## Vercel Deployments

### Build fails — "flutter: command not found"

Flutter is not pre-installed on Vercel. The build command must reference the locally cloned flutter binary: `flutter/bin/flutter build web ...`

Add an `install.sh` to the Flutter project root:
```bash
#!/bin/bash
git clone https://github.com/flutter/flutter.git --depth 1 -b stable flutter
flutter/bin/flutter pub get
```

Set Vercel **Install Command** to `bash install.sh`.

### Wrong project is being deployed

Check the **Root Directory** setting in Vercel project settings. Each Flutter project must have its own root directory set:
- Admin UI → `wrapper/flutter_wrapper`
- Mentor registration → `flutter_mentor`
- Mentee registration → `flutter_mentee`

### Google Form submission fails

Check the Node.js function logs in Vercel (Deployments → Runtime Logs). Common issues:
- `MENTOR_GOOGLE_FORM_ENABLED` not set → defaults to `true`, form submission should run
- Google Form field IDs changed → update `flutter_mentor/api/_lib/mentor_form_definition.js`

---

## Testing Endpoints with curl

```bash
BASE=https://YOUR-SERVICE.onrender.com

# Health check
curl $BASE/health

# Config list (no auth)
curl $BASE/config/orgs

# Login
TOKEN=$(curl -s -X POST $BASE/login \
  -H "Content-Type: application/json" \
  -d '{"username":"devaccount","password":"yourpassword"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# List mentors
curl -H "Authorization: Bearer $TOKEN" $BASE/mentors

# Match history
curl -H "Authorization: Bearer $TOKEN" $BASE/match-results

# Get orgs (admin)
curl -H "Authorization: Bearer $TOKEN" $BASE/get_orgs
```

## Inspecting Render Logs

Render dashboard → service → **Logs** tab.

Key things to search for:
- `ERROR` — Python exceptions
- `cors_config` — shows CORS origins loaded at startup
- `run_match_request` — each matching request
- `run_match_response` — result and duration
- `config_list_db_read_failed` — DB connection issues
- `match_result_db_store_failed` — failed to save match result
