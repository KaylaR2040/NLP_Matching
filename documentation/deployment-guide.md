# Deployment Guide

## Scope

This guide is only about deploying the FastAPI backend to Vercel and using the correct local Python environment before running backend commands.

## Use The Backend Virtual Environment Locally

For local backend commands, use `wrapper/backend/.venv`.

Create or recreate it:

```bash
cd wrapper/backend
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python -m ensurepip --upgrade
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

Important:

- use this virtualenv for local `python`, `pip`, `uvicorn`, and import checks
- do not assume Vercel uses this virtualenv
- Vercel builds its own Python environment from the selected root and `requirements.txt`

## Recommended Vercel Root

Use:

```text
Root Directory: wrapper/backend
```

Reason:

- `wrapper/backend/api/index.py` is the clean backend entrypoint
- `wrapper/backend/requirements.txt` is the backend-local manifest
- `wrapper/backend/vercel.json` has the correct relative build command

## Required Vercel Settings

Recommended settings:

- `Root Directory`: `wrapper/backend`
- `Build Command`: `python scripts/prepare_vercel_bundle.py`
- `Install Command`: leave unset unless you have a specific reason to override it

If you intentionally deploy from repo root instead:

- `Root Directory`: repository root
- `Build Command`: `python wrapper/backend/scripts/prepare_vercel_bundle.py`

## Deploy Commands

Local backend setup:

```bash
cd wrapper/backend
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Optional local Vercel reproduction:

```bash
cd wrapper/backend
source .venv/bin/activate
vercel pull --yes
vercel build
```

## Runtime Diagnostics In Logs

The entrypoints now emit a `[wrapper.runtime-diagnostics]` log line before importing `app.main`.

Use that line in Vercel logs to verify:

- `python_executable`
- `python_version`
- `sys_prefix`
- `sys_base_prefix`
- `VIRTUAL_ENV`
- `PYTHONPATH`
- whether `pandas` is discoverable before the app import

## Deploy Checklist

1. Recreate and activate `wrapper/backend/.venv`.
2. Install `wrapper/backend/requirements.txt`.
3. Verify local import works.
4. Set Vercel `Root Directory` to `wrapper/backend`.
5. Set Vercel `Build Command` to `python scripts/prepare_vercel_bundle.py`.
6. Deploy.
7. Check runtime logs for `[wrapper.runtime-diagnostics]`.
8. Confirm `pandas_spec_found` is `true`.
