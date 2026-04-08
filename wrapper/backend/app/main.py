from __future__ import annotations

import base64
from collections import defaultdict, deque
import hashlib
import hmac
import json
import logging
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Optional, Set, Tuple

import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import (
    DevFileRequest,
    DevFileSaveRequest,
    ExportAssignmentsRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    RunMatchPayload,
    SaveMajorsRequest,
    ScriptRequest,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
NLP_PROJECT_DIR = REPO_ROOT / "nlp_project"
NLP_MAIN_PATH = NLP_PROJECT_DIR / "main.py"
DATA_DIR = REPO_ROOT / "data"
ORGS_PATH = DATA_DIR / "ncsu_orgs.txt"
CONCENTRATIONS_PATH = DATA_DIR / "concentrations.txt"
GRAD_PROGRAMS_PATH = DATA_DIR / "grad_programs.txt"
ABM_PROGRAMS_PATH = DATA_DIR / "abm_programs.txt"
PHD_PROGRAMS_PATH = DATA_DIR / "phd_programs.txt"
DEFAULT_MAJORS_PATH = GRAD_PROGRAMS_PATH
DEV_BACKUP_DIR = REPO_ROOT / "wrapper" / "backend" / "data" / "dev_file_backups"
BACKEND_ENV_PATH = REPO_ROOT / "wrapper" / "backend" / ".env"

load_dotenv(BACKEND_ENV_PATH)

TOKEN_TTL_SECONDS = int(os.getenv("WRAPPER_TOKEN_TTL_SECONDS", "3600"))
MAX_SESSIONS_PER_USER = int(os.getenv("WRAPPER_MAX_SESSIONS_PER_USER", "5"))
REQUIRE_HTTPS = os.getenv("WRAPPER_REQUIRE_HTTPS", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

LOGIN_WINDOW_SECONDS = int(os.getenv("WRAPPER_LOGIN_WINDOW_SECONDS", "300"))
LOGIN_MAX_ATTEMPTS_PER_IP = int(os.getenv("WRAPPER_LOGIN_MAX_ATTEMPTS_PER_IP", "20"))
LOGIN_MAX_ATTEMPTS_PER_USER = int(os.getenv("WRAPPER_LOGIN_MAX_ATTEMPTS_PER_USER", "10"))
LOGIN_LOCKOUT_SECONDS = int(os.getenv("WRAPPER_LOGIN_LOCKOUT_SECONDS", "600"))

DEV_EDITABLE_FILES: Dict[str, Dict[str, Any]] = {
    "ncsu_orgs": {
        "label": "NCSU Organizations",
        "path": ORGS_PATH,
        "script_kind": "orgs",
    },
    "concentrations": {
        "label": "Concentrations",
        "path": CONCENTRATIONS_PATH,
        "script_kind": "concentrations",
    },
    "abm_programs": {
        "label": "ABM Programs",
        "path": ABM_PROGRAMS_PATH,
        "script_kind": None,
    },
    "grad_programs": {
        "label": "Graduate Programs",
        "path": GRAD_PROGRAMS_PATH,
        "script_kind": None,
    },
    "phd_programs": {
        "label": "PhD Programs",
        "path": PHD_PROGRAMS_PATH,
        "script_kind": None,
    },
}


@dataclass
class AuthRecord:
    username: str
    password_hash: str
    is_dev: bool


@dataclass
class AuthSession:
    username: str
    is_dev: bool
    issued_at: float
    expires_at: float


@dataclass
class AuthContext:
    token: str
    session: AuthSession


@dataclass
class LoginRateBucket:
    attempts: Deque[float]
    lockout_until: float


security = HTTPBearer(auto_error=False)
SESSION_TOKENS: Dict[str, AuthSession] = {}
FAILED_ATTEMPTS_BY_IP: Dict[str, LoginRateBucket] = defaultdict(
    lambda: LoginRateBucket(attempts=deque(), lockout_until=0.0)
)
FAILED_ATTEMPTS_BY_USER: Dict[str, LoginRateBucket] = defaultdict(
    lambda: LoginRateBucket(attempts=deque(), lockout_until=0.0)
)
LOG = logging.getLogger("wrapper.auth")


app = FastAPI(title="NLP Mentor Matcher Wrapper API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_https_transport(request: Request, call_next):
    if not REQUIRE_HTTPS:
        return await call_next(request)

    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    scheme = request.url.scheme.lower()
    host = request.headers.get("host", "").split(":")[0].strip().lower()
    ip = _client_ip(request)
    localhost_hosts: Set[str] = {"localhost", "127.0.0.1", "::1"}
    is_local = host in localhost_hosts or ip in localhost_hosts
    is_https = scheme == "https" or forwarded_proto == "https"

    if not is_https and not is_local:
        LOG.warning("https_required_block ip=%s host=%s path=%s", ip, host, request.url.path)
        return JSONResponse(status_code=400, content={"detail": "HTTPS is required"})

    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def _b64decode_nopad(value: str) -> bytes:
    pad_len = (-len(value)) % 4
    return base64.urlsafe_b64decode(value + ("=" * pad_len))


def _load_auth_records() -> List[AuthRecord]:
    user_username = os.getenv("WRAPPER_USER_USERNAME", "").strip()
    user_password_hash = os.getenv("WRAPPER_USER_PASSWORD_HASH", "").strip()
    dev_username = os.getenv("WRAPPER_DEV_USERNAME", "").strip()
    dev_password_hash = os.getenv("WRAPPER_DEV_PASSWORD_HASH", "").strip()

    if not all([user_username, user_password_hash, dev_username, dev_password_hash]):
        raise HTTPException(
            status_code=503,
            detail=(
                "Auth is not configured. Set WRAPPER_USER_USERNAME, WRAPPER_USER_PASSWORD_HASH, "
                "WRAPPER_DEV_USERNAME, and WRAPPER_DEV_PASSWORD_HASH in backend environment."
            ),
        )

    return [
        AuthRecord(username=user_username, password_hash=user_password_hash, is_dev=False),
        AuthRecord(username=dev_username, password_hash=dev_password_hash, is_dev=True),
    ]


def _verify_pbkdf2_password(password: str, encoded_hash: str) -> bool:
    # Format: pbkdf2_sha256$<iterations>$<base64url_salt>$<base64url_hash>
    try:
        algorithm, iter_text, salt_text, expected_text = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iter_text)
        salt = _b64decode_nopad(salt_text)
        expected = _b64decode_nopad(expected_text)
    except Exception:
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def _cleanup_expired_sessions() -> None:
    now = time.time()
    expired_tokens = [token for token, session in SESSION_TOKENS.items() if session.expires_at <= now]
    for token in expired_tokens:
        SESSION_TOKENS.pop(token, None)


def _issue_token(*, username: str, is_dev: bool) -> Tuple[str, AuthSession]:
    _cleanup_expired_sessions()
    now = time.time()
    sessions_for_user = sorted(
        [
            (token, session)
            for token, session in SESSION_TOKENS.items()
            if session.username == username and session.is_dev == is_dev
        ],
        key=lambda pair: pair[1].issued_at,
    )
    while len(sessions_for_user) >= max(1, MAX_SESSIONS_PER_USER):
        token_to_drop, _ = sessions_for_user.pop(0)
        SESSION_TOKENS.pop(token_to_drop, None)

    token = secrets.token_urlsafe(32)
    expires_at = now + TOKEN_TTL_SECONDS
    session = AuthSession(
        username=username,
        is_dev=is_dev,
        issued_at=now,
        expires_at=expires_at,
    )
    SESSION_TOKENS[token] = session
    return token, session


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


def _prune_attempts(bucket: LoginRateBucket, now: float) -> None:
    cutoff = now - max(1, LOGIN_WINDOW_SECONDS)
    while bucket.attempts and bucket.attempts[0] < cutoff:
        bucket.attempts.popleft()


def _is_rate_limited(ip: str, username: str, now: float) -> bool:
    ip_bucket = FAILED_ATTEMPTS_BY_IP[ip]
    user_bucket = FAILED_ATTEMPTS_BY_USER[username]
    _prune_attempts(ip_bucket, now)
    _prune_attempts(user_bucket, now)
    return now < ip_bucket.lockout_until or now < user_bucket.lockout_until


def _record_login_failure(ip: str, username: str, now: float) -> None:
    ip_bucket = FAILED_ATTEMPTS_BY_IP[ip]
    user_bucket = FAILED_ATTEMPTS_BY_USER[username]
    _prune_attempts(ip_bucket, now)
    _prune_attempts(user_bucket, now)

    ip_bucket.attempts.append(now)
    user_bucket.attempts.append(now)

    if len(ip_bucket.attempts) >= max(1, LOGIN_MAX_ATTEMPTS_PER_IP):
        ip_bucket.lockout_until = max(ip_bucket.lockout_until, now + LOGIN_LOCKOUT_SECONDS)
    if len(user_bucket.attempts) >= max(1, LOGIN_MAX_ATTEMPTS_PER_USER):
        user_bucket.lockout_until = max(user_bucket.lockout_until, now + LOGIN_LOCKOUT_SECONDS)


def _reset_login_failures(ip: str, username: str) -> None:
    FAILED_ATTEMPTS_BY_IP.pop(ip, None)
    FAILED_ATTEMPTS_BY_USER.pop(username, None)


def _require_auth_context(*, require_dev: bool = False):
    def dependency(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ) -> AuthContext:
        _cleanup_expired_sessions()
        ip = _client_ip(request)
        if credentials is None or credentials.scheme.lower() != "bearer":
            LOG.warning("auth_missing_token ip=%s path=%s", ip, request.url.path)
            raise HTTPException(status_code=401, detail="Missing bearer token")

        token = credentials.credentials.strip()
        session = SESSION_TOKENS.get(token)
        if session is None:
            LOG.warning("auth_invalid_token ip=%s path=%s", ip, request.url.path)
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if require_dev and not session.is_dev:
            LOG.warning(
                "auth_forbidden_dev_endpoint ip=%s path=%s user=%s",
                ip,
                request.url.path,
                session.username,
            )
            raise HTTPException(status_code=403, detail="Dev role required")
        return AuthContext(token=token, session=session)

    return dependency


def _require_auth(*, require_dev: bool = False):
    def dependency(context: AuthContext = Depends(_require_auth_context(require_dev=require_dev))) -> AuthSession:
        return context.session

    return dependency


def _audit_dev_action(action: str, session: AuthSession) -> None:
    LOG.info("dev_action action=%s username=%s", action, session.username)


def _pair_key(mentee_id: str, mentor_id: str) -> str:
    return f"{mentee_id}::{mentor_id}"


def _dev_file_entry(file_key: str) -> Dict[str, Any]:
    entry = DEV_EDITABLE_FILES.get(file_key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Unknown dev file key: {file_key}")
    return entry


def _dev_file_path(file_key: str) -> Path:
    return Path(_dev_file_entry(file_key)["path"]).resolve()


def _list_dev_file_entries() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for key, entry in DEV_EDITABLE_FILES.items():
        path = Path(entry["path"]).resolve()
        file_info = _read_text_file(path)
        rows.append(
            {
                "file_key": key,
                "label": str(entry["label"]),
                "path": file_info["path"],
                "line_count": file_info["line_count"],
                "has_update_script": bool(entry.get("script_kind")),
            }
        )
    rows.sort(key=lambda item: str(item["label"]).lower())
    return rows


def _backup_current_file(path: Path, file_key: str) -> Optional[Path]:
    if not path.exists():
        return None
    timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    backup_dir = DEV_BACKUP_DIR / file_key
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{timestamp}.txt"
    shutil.copy2(path, backup_path)
    return backup_path


def _write_text_file_with_backup(path: Path, text: str, file_key: str) -> Dict[str, Any]:
    backup_path = _backup_current_file(path, file_key)
    payload = _write_text_file(path, text)
    payload["backup_path"] = str(backup_path) if backup_path else None
    return payload


def _latest_backup_path(file_key: str) -> Optional[Path]:
    backup_dir = DEV_BACKUP_DIR / file_key
    if not backup_dir.exists():
        return None
    candidates = sorted(
        [item for item in backup_dir.glob("*.txt") if item.is_file()],
        key=lambda item: item.stat().st_mtime,
    )
    if not candidates:
        return None
    return candidates[-1]


def _revert_file_from_latest_backup(file_key: str) -> Dict[str, Any]:
    latest = _latest_backup_path(file_key)
    if latest is None:
        raise HTTPException(status_code=404, detail="No backup exists for this file")
    target = _dev_file_path(file_key)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(latest, target)
    payload = _read_text_file(target)
    payload["reverted_from"] = str(latest)
    return payload


def _validate_payload(raw: Dict[str, Any]) -> RunMatchPayload:
    if hasattr(RunMatchPayload, "model_validate"):
        return RunMatchPayload.model_validate(raw)  # Pydantic v2
    return RunMatchPayload.parse_obj(raw)  # Pydantic v1


def _pair_rows(pairs: Iterable[Any]) -> List[str]:
    rows: List[str] = []
    for pair in pairs:
        mentee_id = str(getattr(pair, "mentee_id", "")).strip()
        mentor_id = str(getattr(pair, "mentor_id", "")).strip()
        if mentee_id and mentor_id:
            rows.append(_pair_key(mentee_id, mentor_id))
    return rows


def _state_dict(payload: RunMatchPayload) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "excluded_mentee_ids": payload.excluded_mentee_ids,
        "excluded_mentor_ids": payload.excluded_mentor_ids,
        "rejected_pairs": _pair_rows(payload.rejected_pairs),
        "locked_pairs": _pair_rows(payload.locked_pairs),
        "global_weights": payload.global_weights,
        "mentee_weight_overrides": payload.mentee_weight_overrides,
        "run_count": 0,
    }


def _as_csv(upload_name: str, content: bytes, out_csv: Path) -> None:
    suffix = Path(upload_name or "").suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        try:
            frame = pd.read_excel(BytesIO(content), dtype=str)
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=400, detail=f"Could not read Excel file '{upload_name}': {exc}") from exc
        frame = frame.fillna("")
        frame.to_csv(out_csv, index=False)
        return

    if suffix and suffix != ".csv":
        raise HTTPException(status_code=400, detail=f"Unsupported file type for '{upload_name}'. Use CSV or Excel.")

    out_csv.write_bytes(content)


def _load_payload(payload_json: str) -> RunMatchPayload:
    try:
        raw = json.loads(payload_json) if payload_json.strip() else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload_json: {exc}") from exc
    return _validate_payload(raw)


def _script_candidates(kind: str) -> List[Path]:
    if kind == "orgs":
        return [
            REPO_ROOT / "wrapper" / "backend" / "scripts" / "pull_orgs.py",
            REPO_ROOT / "data" / "pullorgs.py",
            REPO_ROOT / "data" / "update_ncsu_orgs.py",
            REPO_ROOT / "flutter_mentor" / "python_scripts" / "update_ncsu_orgs.py",
        ]
    if kind == "concentrations":
        return [
            REPO_ROOT / "wrapper" / "backend" / "scripts" / "pull_concentrations.py",
            REPO_ROOT / "data" / "pullconcentration.py",
            REPO_ROOT / "data" / "pullconcentrations.py",
            REPO_ROOT / "data" / "update_concentrations.py",
            REPO_ROOT / "flutter_mentor" / "python_scripts" / "update_concentrations.py",
        ]
    return []


def _run_script(script_path: Path, args: Optional[List[str]] = None) -> Dict[str, Any]:
    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"Script not found: {script_path}")

    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    completed = subprocess.run(
        cmd,
        cwd=str(script_path.parent),
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Script execution failed",
                "script": str(script_path),
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )

    return {
        "status": "ok",
        "script": str(script_path),
        "command": cmd,
        "stdout": completed.stdout,
    }


def _run_script_with_output_fallback(script_path: Path, output_path: Path) -> Dict[str, Any]:
    try:
        return _run_script(script_path, args=["--output", str(output_path)])
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        stderr = str(detail.get("stderr", ""))
        if "unrecognized arguments: --output" in stderr:
            return _run_script(script_path)
        raise


def _read_text_file(path: Path) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    line_count = len([line for line in text.splitlines() if line.strip()])
    return {"path": str(path), "text": text, "line_count": line_count}


def _write_text_file(path: Path, text: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.replace("\r\n", "\n")
    path.write_text(normalized, encoding="utf-8")
    line_count = len([line for line in normalized.splitlines() if line.strip()])
    return {"status": "ok", "path": str(path), "line_count": line_count}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, http_request: Request) -> LoginResponse:
    records = _load_auth_records()
    username = request.username.strip()
    password = request.password
    now = time.time()
    ip = _client_ip(http_request)
    username_key = username.lower()

    if _is_rate_limited(ip=ip, username=username_key, now=now):
        LOG.warning("login_rate_limited ip=%s username=%s", ip, username)
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    for record in records:
        if username != record.username:
            continue
        if not _verify_pbkdf2_password(password, record.password_hash):
            break
        token, _session = _issue_token(username=record.username, is_dev=record.is_dev)
        _reset_login_failures(ip=ip, username=username_key)
        LOG.info("login_success ip=%s username=%s is_dev=%s", ip, record.username, record.is_dev)
        return LoginResponse(
            token=token,
            expires_in=TOKEN_TTL_SECONDS,
            is_dev=record.is_dev,
            username=record.username,
        )
    _record_login_failure(ip=ip, username=username_key, now=now)
    LOG.warning("login_failed ip=%s username=%s", ip, username)
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/token/refresh", response_model=LoginResponse)
def refresh_token(context: AuthContext = Depends(_require_auth_context())) -> LoginResponse:
    old_token = context.token
    session = context.session
    SESSION_TOKENS.pop(old_token, None)
    new_token, _new_session = _issue_token(username=session.username, is_dev=session.is_dev)
    LOG.info("token_refreshed username=%s is_dev=%s", session.username, session.is_dev)
    return LoginResponse(
        token=new_token,
        expires_in=TOKEN_TTL_SECONDS,
        is_dev=session.is_dev,
        username=session.username,
    )


@app.post("/logout")
def logout(context: AuthContext = Depends(_require_auth_context())) -> Dict[str, str]:
    session = context.session
    # Drop all tokens for this user and role to invalidate active sessions.
    to_remove = [
        token
        for token, candidate in SESSION_TOKENS.items()
        if candidate.username == session.username and candidate.is_dev == session.is_dev
    ]
    for token in to_remove:
        SESSION_TOKENS.pop(token, None)
    LOG.info("logout username=%s is_dev=%s revoked_tokens=%s", session.username, session.is_dev, len(to_remove))
    return {"status": "ok"}


@app.get("/me", response_model=MeResponse)
def me(session: AuthSession = Depends(_require_auth())) -> MeResponse:
    return MeResponse(
        username=session.username,
        is_dev=session.is_dev,
        expires_at=int(session.expires_at),
    )


@app.post("/run_match")
async def run_match(
    mentee_file: UploadFile = File(...),
    mentor_file: UploadFile = File(...),
    payload_json: str = Form("{}"),
    _session: AuthSession = Depends(_require_auth()),
) -> Dict[str, Any]:
    payload = _load_payload(payload_json)

    if not NLP_MAIN_PATH.exists():
        raise HTTPException(status_code=500, detail=f"Could not find nlp_project/main.py at {NLP_MAIN_PATH}")

    with tempfile.TemporaryDirectory(prefix="matcher_wrapper_") as tmp:
        tmp_dir = Path(tmp)
        output_dir = tmp_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        mentee_csv = tmp_dir / "mentees.csv"
        mentor_csv = tmp_dir / "mentors.csv"
        state_path = tmp_dir / "state.json"

        _as_csv(mentee_file.filename or "mentees.csv", await mentee_file.read(), mentee_csv)
        _as_csv(mentor_file.filename or "mentors.csv", await mentor_file.read(), mentor_csv)
        state_path.write_text(json.dumps(_state_dict(payload), indent=2), encoding="utf-8")

        cmd = [
            sys.executable,
            str(NLP_MAIN_PATH),
            "--mentee-csv",
            str(mentee_csv),
            "--mentor-csv",
            str(mentor_csv),
            "--state-path",
            str(state_path),
            "--output-dir",
            str(output_dir),
            "--top-n",
            str(payload.top_n),
            "run",
        ]

        completed = subprocess.run(cmd, cwd=str(NLP_PROJECT_DIR), capture_output=True, text=True)
        if completed.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Matching pipeline failed",
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                },
            )

        output_json_path = output_dir / "latest_matches.json"
        if not output_json_path.exists():
            raise HTTPException(status_code=500, detail="Pipeline completed but latest_matches.json was not found")

        result = json.loads(output_json_path.read_text(encoding="utf-8"))
        return {
            "status": "ok",
            "result": result,
            "stdout": completed.stdout,
        }


@app.post("/update_orgs")
def update_orgs(
    request: ScriptRequest,
    _session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> Dict[str, Any]:
    _audit_dev_action("update_orgs", _session)
    if request.script_path:
        result = _run_script_with_output_fallback(Path(request.script_path).expanduser(), ORGS_PATH)
        result["file"] = _read_text_file(ORGS_PATH)
        return result

    for candidate in _script_candidates("orgs"):
        if candidate.exists():
            result = _run_script_with_output_fallback(candidate, ORGS_PATH)
            result["file"] = _read_text_file(ORGS_PATH)
            return result

    raise HTTPException(
        status_code=404,
        detail=(
            "No org-update script found. Pass script_path in request body or add one of the expected scripts."
        ),
    )


@app.post("/update_concentrations")
def update_concentrations(
    request: ScriptRequest,
    _session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> Dict[str, Any]:
    _audit_dev_action("update_concentrations", _session)
    if request.script_path:
        result = _run_script_with_output_fallback(
            Path(request.script_path).expanduser(),
            CONCENTRATIONS_PATH,
        )
        result["file"] = _read_text_file(CONCENTRATIONS_PATH)
        return result

    for candidate in _script_candidates("concentrations"):
        if candidate.exists():
            result = _run_script_with_output_fallback(candidate, CONCENTRATIONS_PATH)
            result["file"] = _read_text_file(CONCENTRATIONS_PATH)
            return result

    raise HTTPException(
        status_code=404,
        detail=(
            "No concentrations-update script found. Pass script_path in request body or add one of the expected scripts."
        ),
    )


@app.get("/dev/files")
def list_dev_files(_session: AuthSession = Depends(_require_auth(require_dev=True))) -> Dict[str, Any]:
    _audit_dev_action("list_dev_files", _session)
    return {"files": _list_dev_file_entries()}


@app.get("/dev/file/{file_key}")
def get_dev_file(file_key: str, _session: AuthSession = Depends(_require_auth(require_dev=True))) -> Dict[str, Any]:
    _audit_dev_action(f"get_dev_file:{file_key}", _session)
    entry = _dev_file_entry(file_key)
    file_info = _read_text_file(_dev_file_path(file_key))
    file_info["file_key"] = file_key
    file_info["label"] = str(entry["label"])
    file_info["has_update_script"] = bool(entry.get("script_kind"))
    return file_info


@app.post("/dev/file/save")
def save_dev_file(
    request: DevFileSaveRequest,
    _session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> Dict[str, Any]:
    _audit_dev_action(f"save_dev_file:{request.file_key}", _session)
    entry = _dev_file_entry(request.file_key)
    payload = _write_text_file_with_backup(
        _dev_file_path(request.file_key),
        request.text,
        request.file_key,
    )
    payload["file_key"] = request.file_key
    payload["label"] = str(entry["label"])
    return payload


@app.post("/dev/file/revert-last")
def revert_dev_file(
    request: DevFileRequest,
    _session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> Dict[str, Any]:
    _audit_dev_action(f"revert_dev_file:{request.file_key}", _session)
    entry = _dev_file_entry(request.file_key)
    payload = _revert_file_from_latest_backup(request.file_key)
    payload["file_key"] = request.file_key
    payload["label"] = str(entry["label"])
    return payload


@app.post("/dev/file/run-update")
def run_dev_file_update(
    request: DevFileRequest,
    _session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> Dict[str, Any]:
    _audit_dev_action(f"run_dev_file_update:{request.file_key}", _session)
    entry = _dev_file_entry(request.file_key)
    script_kind = entry.get("script_kind")
    if not script_kind:
        raise HTTPException(status_code=400, detail="No update script configured for this file")

    output_path = _dev_file_path(request.file_key)
    for candidate in _script_candidates(str(script_kind)):
        if candidate.exists():
            result = _run_script_with_output_fallback(candidate, output_path)
            result["file"] = _read_text_file(output_path)
            result["file_key"] = request.file_key
            result["label"] = str(entry["label"])
            return result

    raise HTTPException(status_code=404, detail=f"No update script found for {request.file_key}")


@app.get("/get_majors")
def get_majors(_session: AuthSession = Depends(_require_auth(require_dev=True))) -> Dict[str, Any]:
    _audit_dev_action("get_majors", _session)
    majors_path = Path(os.getenv("MAJORS_PATH", str(DEFAULT_MAJORS_PATH))).expanduser().resolve()
    return _read_text_file(majors_path)


@app.post("/save_majors")
def save_majors(
    request: SaveMajorsRequest,
    _session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> Dict[str, Any]:
    _audit_dev_action("save_majors", _session)
    majors_path = Path(os.getenv("MAJORS_PATH", str(DEFAULT_MAJORS_PATH))).expanduser().resolve()
    return _write_text_file(majors_path, request.text)


@app.get("/get_orgs")
def get_orgs(_session: AuthSession = Depends(_require_auth(require_dev=True))) -> Dict[str, Any]:
    _audit_dev_action("get_orgs", _session)
    return _read_text_file(ORGS_PATH)


@app.post("/save_orgs")
def save_orgs(
    request: SaveMajorsRequest,
    _session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> Dict[str, Any]:
    _audit_dev_action("save_orgs", _session)
    return _write_text_file(ORGS_PATH, request.text)


@app.get("/get_concentrations")
def get_concentrations(_session: AuthSession = Depends(_require_auth(require_dev=True))) -> Dict[str, Any]:
    _audit_dev_action("get_concentrations", _session)
    return _read_text_file(CONCENTRATIONS_PATH)


@app.post("/save_concentrations")
def save_concentrations(
    request: SaveMajorsRequest,
    _session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> Dict[str, Any]:
    _audit_dev_action("save_concentrations", _session)
    return _write_text_file(CONCENTRATIONS_PATH, request.text)


@app.post("/export_assignments")
def export_assignments(
    request: ExportAssignmentsRequest,
    _session: AuthSession = Depends(_require_auth()),
) -> StreamingResponse:
    frame = pd.DataFrame(request.rows)
    filename = request.filename if request.filename.lower().endswith(".xlsx") else f"{request.filename}.xlsx"

    output = BytesIO()
    frame.to_excel(output, index=False)
    output.seek(0)

    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
