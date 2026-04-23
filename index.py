from wrapper.backend.app.runtime_diagnostics import emit_runtime_diagnostics

emit_runtime_diagnostics("repo-root index.py")

from wrapper.backend.app.main import app
# This file is used to run the FastAPI application using a WSGI server like Gunicorn.
