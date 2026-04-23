# Verification And Health Checks

## Local Run

Use the backend virtualenv first:

```bash
cd wrapper/backend
source .venv/bin/activate
```

If `.venv` is broken or missing, rebuild it:

```bash
cd wrapper/backend
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python -m ensurepip --upgrade
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

## Local Import Test

Run:

```bash
cd wrapper/backend
source .venv/bin/activate
python -c "from api.index import app; print(app.title)"
```

Expected:

- import succeeds
- app title prints

If this fails with `ModuleNotFoundError: No module named 'pandas'`, your local `.venv` does not have backend dependencies installed correctly.

## Local Server Run

Run:

```bash
cd wrapper/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

## Local HTTP Checks

Run:

```bash
curl -i http://localhost:8000/
curl -i http://localhost:8000/health
curl -i http://localhost:8000/api/health
```

Open:

```text
http://localhost:8000/docs
```

## Production Checks

After deploy, test:

```bash
curl -i https://<backend-url>/
curl -i https://<backend-url>/health
curl -i https://<backend-url>/api/health
```

Open:

```text
https://<backend-url>/docs
```

Then test auth:

```bash
curl -i -X POST https://<backend-url>/login \
  -H "Content-Type: application/json" \
  -d '{"username":"<user>","password":"<password>"}'
```

Then test a protected route:

```bash
curl -i https://<backend-url>/me \
  -H "Authorization: Bearer <token>"
```

## What Counts As Healthy

Treat the backend as healthy only when:

1. import succeeds locally
2. `GET /health` works locally
3. deployed runtime logs do not show `ModuleNotFoundError`
4. `GET /health` works in production
5. `GET /docs` works in production
6. `POST /login` works in production
