# Manual Vercel Debug Session

## Use This When

Use this checklist when:

- deploy says `Ready`
- but requests still fail
- or runtime logs show missing modules like `pandas`

## 1. Check Project Settings

Verify:

- `Root Directory` is `wrapper/backend`
- `Build Command` is `python scripts/prepare_vercel_bundle.py`
- `Install Command` is unset unless intentionally overridden

## 2. Check Build Logs

Look for:

- Python version selected by Vercel
- `requirements.txt` install step
- `pandas` installation lines
- successful `prepare_vercel_bundle.py` execution

If build logs do not show `pandas` installation, the runtime error is expected.

## 3. Check Runtime Logs

Look for the line starting with:

```text
[wrapper.runtime-diagnostics]
```

Read these fields:

- `python_executable`
- `python_version`
- `sys_prefix`
- `sys_base_prefix`
- `virtual_env`
- `pandas_spec_found`
- `pandas_spec_origin`

Interpretation:

- `virtual_env` will usually be empty on Vercel
- `pandas_spec_found: false` means the Vercel runtime cannot discover `pandas`
- `pandas_spec_found: true` means `pandas` is present and the failure is elsewhere

## 4. Check The Failing Import

If logs show:

```text
ModuleNotFoundError: No module named 'pandas'
```

then confirm whether the traceback starts from:

- `api/index.py`
- `index.py`
- `wrapper/backend/api/index.py`

That tells you which deployment path Vercel actually used.

## 5. Fastest Fix Path

1. Set `Root Directory` to `wrapper/backend`.
2. Leave `Install Command` unset.
3. Keep `Build Command` as `python scripts/prepare_vercel_bundle.py`.
4. Redeploy.
5. Re-check `[wrapper.runtime-diagnostics]`.
6. Re-test `/health` and `/docs`.
