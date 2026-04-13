from __future__ import annotations

import base64
import csv
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
from io import BytesIO, StringIO
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
    LinkedInEnrichmentConfigResponse,
    LoginRequest,
    LoginResponse,
    MeResponse,
    MentorBulkDeleteRequest,
    MentorBulkDeleteResponse,
    MentorCreateRequest,
    MentorEnrichmentResponse,
    MentorImportResponse,
    MentorRecord,
    MentorSyncResponse,
    MentorsListResponse,
    MentorUpdateRequest,
    RunMatchPayload,
    SaveMajorsRequest,
    ScriptRequest,
)
from .linkedin_enrichment import (
    build_linkedin_enrichment_service_from_env,
    normalize_linkedin_profile_url,
)
from .mentor_store import DEFAULT_MENTOR_BACKUP_DIR, DEFAULT_MENTOR_STORE_PATH, MentorStore


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
DEFAULT_MENTOR_SOURCE_CSV = REPO_ROOT / "nlp_project" / "data" / "mentor_real.csv"
DEFAULT_MATCHING_STATE_PATH = REPO_ROOT / "nlp_project" / "state" / "matching_state.json"

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

MENTOR_STORE_PATH = Path(
    os.getenv("WRAPPER_MENTOR_STORE_PATH", str(DEFAULT_MENTOR_STORE_PATH))
).expanduser()
MENTOR_BACKUP_DIR = Path(
    os.getenv("WRAPPER_MENTOR_BACKUP_DIR", str(DEFAULT_MENTOR_BACKUP_DIR))
).expanduser()
MENTOR_SOURCE_CSV_PATH = Path(
    os.getenv("WRAPPER_MENTOR_SOURCE_CSV_PATH", str(DEFAULT_MENTOR_SOURCE_CSV))
).expanduser()
MATCHING_STATE_PATH = Path(
    os.getenv("WRAPPER_MATCHING_STATE_PATH", str(DEFAULT_MATCHING_STATE_PATH))
).expanduser()

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
MENTOR_STORE = MentorStore(store_path=MENTOR_STORE_PATH, backup_dir=MENTOR_BACKUP_DIR)
LINKEDIN_ENRICHMENT = build_linkedin_enrichment_service_from_env()


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
    payload["backup_path"] = (
        _normalize_repo_path_for_api(str(backup_path), fallback="")
        if backup_path
        else None
    )
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
    payload["reverted_from"] = _normalize_repo_path_for_api(str(latest), fallback="")
    return payload


def _validate_payload(raw: Dict[str, Any]) -> RunMatchPayload:
    if hasattr(RunMatchPayload, "model_validate"):
        return RunMatchPayload.model_validate(raw)  # Pydantic v2
    return RunMatchPayload.parse_obj(raw)  # Pydantic v1


def _pair_rows(pairs: Iterable[Any]) -> List[str]:
    rows: List[str] = []
    for pair in pairs:
        mentee_id = ""
        mentor_id = ""

        if isinstance(pair, dict):
            mentee_id = str(pair.get("mentee_id", "")).strip()
            mentor_id = str(pair.get("mentor_id", "")).strip()
        elif isinstance(pair, (list, tuple)) and len(pair) >= 2:
            mentee_id = str(pair[0]).strip()
            mentor_id = str(pair[1]).strip()
        elif isinstance(pair, str):
            raw = pair.strip()
            if "::" in raw:
                left, right = raw.split("::", 1)
                mentee_id = left.strip()
                mentor_id = right.strip()
        else:
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
                "script": _normalize_repo_path_for_api(str(script_path), fallback=script_path.name),
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )

    return {
        "status": "ok",
        "script": _normalize_repo_path_for_api(str(script_path), fallback=script_path.name),
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


def _is_timeout_script_failure(detail: Dict[str, Any]) -> bool:
    stderr = str(detail.get("stderr", ""))
    stdout = str(detail.get("stdout", ""))
    combined = f"{stderr}\n{stdout}".lower()
    timeout_markers = (
        "read timed out",
        "readtimeout",
        "socket.timeout",
        "timed out",
        "timeouterror",
        "urllib3.exceptions.readtimeouterror",
        "requests.exceptions.readtimeout",
    )
    return any(marker in combined for marker in timeout_markers)


def _timeout_degraded_result(
    *,
    script_path: Path,
    detail: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "status": "degraded",
        "script": _normalize_repo_path_for_api(str(script_path), fallback=script_path.name),
        "message": (
            "Update script timed out while fetching remote data; "
            "kept the current local file unchanged."
        ),
        "stdout": str(detail.get("stdout", "")),
        "stderr": str(detail.get("stderr", "")),
    }


def _read_text_file(path: Path) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    line_count = len([line for line in text.splitlines() if line.strip()])
    return {
        "path": _normalize_repo_path_for_api(str(path)),
        "text": text,
        "line_count": line_count,
    }


def _write_text_file(path: Path, text: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.replace("\r\n", "\n")
    path.write_text(normalized, encoding="utf-8")
    line_count = len([line for line in normalized.splitlines() if line.strip()])
    return {
        "status": "ok",
        "path": _normalize_repo_path_for_api(str(path)),
        "line_count": line_count,
    }


def _model_dict(instance: Any, *, exclude_unset: bool = False) -> Dict[str, Any]:
    if hasattr(instance, "model_dump"):
        return instance.model_dump(exclude_unset=exclude_unset)  # Pydantic v2
    return instance.dict(exclude_unset=exclude_unset)  # Pydantic v1


def _bool_match(value: str, term: str) -> bool:
    return term in value.lower()


def _normalize_repo_path_for_api(path_value: str, *, fallback: str = "") -> str:
    if not path_value:
        return fallback
    value = Path(path_value)
    try:
        relative = value.resolve().relative_to(REPO_ROOT)
        return str(relative)
    except Exception:
        return value.name


def _normalize_source_path_for_api(path_value: str, *, fallback: str = "nlp_project/data/mentor_real.csv") -> str:
    return _normalize_repo_path_for_api(path_value, fallback=fallback)


def _mentor_record_for_api(record: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(record)
    payload["source_csv_path"] = _normalize_source_path_for_api(str(payload.get("source_csv_path", "")))
    payload.pop("enrichment_provider_metadata", None)
    return payload


def _csv_text(row: Dict[str, Any], key: str) -> str:
    return str(row.get(key, "")).strip()


LINKEDIN_RECORD_ALIAS_KEYS: List[str] = [
    "linkedin_url",
    "linkedin",
    "linkedinUrl",
    "linkedinURL",
    "profile_link",
    "profileLink",
    "profile_url",
    "profileUrl",
    "profile",
]

LINKEDIN_EXTRA_ALIAS_HEADERS: Set[str] = {
    "linkedin",
    "linkedin url",
    "linkedin_url",
    "linkedin profile",
    "linkedin profile url",
    "profile link",
    "profile url",
    "linkedin profile link",
}


def _header_key(value: str) -> str:
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def _collect_linkedin_field_values(record: Dict[str, Any]) -> Dict[str, str]:
    found: Dict[str, str] = {}
    for key in LINKEDIN_RECORD_ALIAS_KEYS:
        value = str(record.get(key, "")).strip()
        if value:
            found[key] = value

    extras = record.get("extra_fields")
    if isinstance(extras, dict):
        for key, value in extras.items():
            if _header_key(str(key)) not in LINKEDIN_EXTRA_ALIAS_HEADERS:
                continue
            text = str(value).strip()
            if text:
                found[f"extra_fields.{key}"] = text
    return found


def _resolve_record_linkedin_url(record: Dict[str, Any]) -> Tuple[str, str, str, Dict[str, str]]:
    raw_fields = _collect_linkedin_field_values(record)
    selected_source = ""
    selected_raw = ""

    for key in LINKEDIN_RECORD_ALIAS_KEYS:
        value = raw_fields.get(key, "").strip()
        if value:
            selected_source = key
            selected_raw = value
            break

    if not selected_raw:
        for key, value in raw_fields.items():
            if not key.startswith("extra_fields."):
                continue
            if value.strip():
                selected_source = key
                selected_raw = value.strip()
                break

    normalized_url = ""
    if selected_raw:
        normalized_url, _ = normalize_linkedin_profile_url(selected_raw)
        return selected_raw, normalized_url, selected_source, raw_fields

    fallback = _lookup_canonical_mentor_profile_fallback(record)
    fallback_url = str(fallback.get("linkedin_url", "")).strip()
    if fallback_url:
        fallback_normalized, _ = normalize_linkedin_profile_url(fallback_url)
        return fallback_url, fallback_normalized, "csv_fallback.linkedin_url", raw_fields

    return "", "", "", raw_fields


def _lookup_canonical_mentor_profile_fallback(record: Dict[str, Any]) -> Dict[str, str]:
    source_path = MENTOR_SOURCE_CSV_PATH
    if not source_path.exists():
        return {}

    record_linkedin = _csv_text(record, "linkedin_url")
    normalized_record_linkedin = ""
    if record_linkedin:
        normalized_record_linkedin, _ = normalize_linkedin_profile_url(record_linkedin)
    record_email = _csv_text(record, "email").lower()

    try:
        with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row_linkedin = _csv_text(row, "LinkedIn")
                normalized_row_linkedin = ""
                if row_linkedin:
                    normalized_row_linkedin, _ = normalize_linkedin_profile_url(row_linkedin)
                row_email = _csv_text(row, "Email").lower()

                matches_linkedin = bool(
                    normalized_record_linkedin
                    and normalized_row_linkedin
                    and normalized_record_linkedin == normalized_row_linkedin
                )
                matches_email = bool(record_email and row_email and record_email == row_email)
                if not (matches_linkedin or matches_email):
                    continue

                fallback: Dict[str, str] = {}
                mappings = {
                    "LinkedIn": "linkedin_url",
                    "Profile Photo URL": "profile_photo_url",
                    "Current Company": "current_company",
                    "Current Job Title": "current_job_title",
                    "Current City State": "current_location",
                    "Current City": "current_city",
                    "Current State": "current_state",
                }
                for source_key, target_key in mappings.items():
                    value = _csv_text(row, source_key)
                    if value:
                        fallback[target_key] = value

                if (
                    "current_location" not in fallback
                    and ("current_city" in fallback or "current_state" in fallback)
                ):
                    fallback["current_location"] = ", ".join(
                        part
                        for part in [
                            fallback.get("current_city", "").strip(),
                            fallback.get("current_state", "").strip(),
                        ]
                        if part
                    )
                return fallback
    except Exception as exc:
        LOG.warning(
            "linkedin_csv_fallback_read_failed path=%s error=%s",
            source_path,
            exc,
        )
        return {}

    return {}


def _parse_pair_rows_for_api(pairs: Iterable[Any]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for pair in pairs:
        mentee_id = ""
        mentor_id = ""
        if isinstance(pair, str) and "::" in pair:
            left, right = pair.split("::", 1)
            mentee_id = left.strip()
            mentor_id = right.strip()
        elif isinstance(pair, dict):
            mentee_id = str(pair.get("mentee_id", "")).strip()
            mentor_id = str(pair.get("mentor_id", "")).strip()
        elif isinstance(pair, (list, tuple)) and len(pair) >= 2:
            mentee_id = str(pair[0]).strip()
            mentor_id = str(pair[1]).strip()
        if mentee_id and mentor_id:
            rows.append(
                {
                    "mentee_id": mentee_id,
                    "mentor_id": mentor_id,
                }
            )
    return rows


def _load_matching_state_for_api(state_path: Path) -> Dict[str, Any]:
    if not state_path.exists():
        return {
            "path": _normalize_repo_path_for_api(str(state_path)),
            "excluded_mentee_ids": [],
            "excluded_mentor_ids": [],
            "rejected_pairs": [],
            "locked_pairs": [],
            "counts": {
                "excluded_mentee_ids": 0,
                "excluded_mentor_ids": 0,
                "rejected_pairs": 0,
                "locked_pairs": 0,
            },
        }

    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}

    excluded_mentee_ids = [str(item).strip() for item in payload.get("excluded_mentee_ids", []) if str(item).strip()]
    excluded_mentor_ids = [str(item).strip() for item in payload.get("excluded_mentor_ids", []) if str(item).strip()]
    rejected_pairs = _parse_pair_rows_for_api(payload.get("rejected_pairs", []))
    locked_pairs = _parse_pair_rows_for_api(payload.get("locked_pairs", []))

    return {
        "path": _normalize_repo_path_for_api(str(state_path)),
        "excluded_mentee_ids": excluded_mentee_ids,
        "excluded_mentor_ids": excluded_mentor_ids,
        "rejected_pairs": rejected_pairs,
        "locked_pairs": locked_pairs,
        "counts": {
            "excluded_mentee_ids": len(excluded_mentee_ids),
            "excluded_mentor_ids": len(excluded_mentor_ids),
            "rejected_pairs": len(rejected_pairs),
            "locked_pairs": len(locked_pairs),
        },
    }


def _extract_mentor_capacity_map(mentor_csv_path: Path) -> Dict[str, int]:
    try:
        if str(NLP_PROJECT_DIR) not in sys.path:
            sys.path.insert(0, str(NLP_PROJECT_DIR))
        from mentor_matching.parsing import parse_mentor_csv  # type: ignore

        mentors = parse_mentor_csv(mentor_csv_path)
        capacities: Dict[str, int] = {}
        for mentor in mentors:
            mentor_id = str(getattr(mentor, "mentor_id", "")).strip()
            if not mentor_id:
                continue
            raw_capacity = getattr(mentor, "max_mentees", 1)
            try:
                capacity = max(1, int(raw_capacity))
            except (TypeError, ValueError):
                capacity = 1
            capacities[mentor_id] = capacity
        return capacities
    except Exception as exc:
        LOG.warning("mentor_capacity_parse_failed path=%s error=%s", mentor_csv_path, exc)
        return {}


def _attach_mentor_capacity_metadata(result: Dict[str, Any], capacities: Dict[str, int]) -> None:
    assignments = result.get("assignments")
    ranked_pairs = result.get("top_ranked_pairs")
    if not isinstance(assignments, list) or not isinstance(ranked_pairs, list):
        return

    assigned_count: Dict[str, int] = defaultdict(int)
    mentor_ids: Set[str] = set()
    for row in assignments:
        if not isinstance(row, dict):
            continue
        mentor_id = str(row.get("mentor_id", "")).strip()
        if not mentor_id:
            continue
        assigned_count[mentor_id] += 1
        mentor_ids.add(mentor_id)

    for row in ranked_pairs:
        if not isinstance(row, dict):
            continue
        mentor_id = str(row.get("mentor_id", "")).strip()
        if mentor_id:
            mentor_ids.add(mentor_id)

    summary: Dict[str, Dict[str, int]] = {}
    for mentor_id in mentor_ids:
        cap = capacities.get(mentor_id)
        if cap is None:
            cap = max(1, assigned_count.get(mentor_id, 1))
        assigned = assigned_count.get(mentor_id, 0)
        summary[mentor_id] = {
            "max_mentees": max(1, int(cap)),
            "assigned_count": assigned,
            "remaining_slots": max(int(cap) - assigned, 0),
        }

    for row in [*assignments, *ranked_pairs]:
        if not isinstance(row, dict):
            continue
        mentor_id = str(row.get("mentor_id", "")).strip()
        if not mentor_id:
            continue
        capacity = summary.get(mentor_id)
        if capacity is None:
            continue
        row["mentor_capacity"] = capacity["max_mentees"]
        row["mentor_assigned_count"] = capacity["assigned_count"]
        row["mentor_remaining_slots"] = capacity["remaining_slots"]

    result["mentor_capacity"] = summary


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


@app.get("/mentors", response_model=MentorsListResponse)
def list_mentors(
    q: str = "",
    active_only: bool = False,
    has_linkedin: Optional[bool] = None,
    company: str = "",
    location: str = "",
    offset: int = 0,
    limit: int = 200,
    _session: AuthSession = Depends(_require_auth()),
) -> MentorsListResponse:
    records = MENTOR_STORE.load_records()

    query = q.strip().lower()
    company_term = company.strip().lower()
    location_term = location.strip().lower()

    filtered: List[Dict[str, Any]] = []
    for record in records:
        is_active = bool(record.get("is_active", True))
        linkedin_url = str(record.get("linkedin_url", "")).strip()

        if active_only and not is_active:
            continue
        if has_linkedin is True and not linkedin_url:
            continue
        if has_linkedin is False and linkedin_url:
            continue
        if company_term and not _bool_match(str(record.get("current_company", "")), company_term):
            continue

        location_text = " ".join(
            [
                str(record.get("current_location", "")),
                str(record.get("current_city", "")),
                str(record.get("current_state", "")),
            ]
        )
        if location_term and not _bool_match(location_text, location_term):
            continue

        if query:
            haystack = " ".join(
                [
                    str(record.get("mentor_id", "")),
                    str(record.get("email", "")),
                    str(record.get("full_name", "")),
                    str(record.get("current_company", "")),
                    str(record.get("current_job_title", "")),
                    str(record.get("current_location", "")),
                    str(record.get("industry_focus_area", "")),
                ]
            ).lower()
            if query not in haystack:
                continue

        filtered.append(record)

    filtered.sort(key=lambda row: str(row.get("full_name", "")).strip().lower())
    total = len(filtered)
    bounded_offset = max(0, offset)
    bounded_limit = min(max(1, limit), 1000)
    page = filtered[bounded_offset : bounded_offset + bounded_limit]

    items = [MentorRecord(**_mentor_record_for_api(row)) for row in page]
    return MentorsListResponse(items=items, total=total)


@app.post("/mentors/import-csv", response_model=MentorImportResponse)
async def import_mentors_csv(
    file: UploadFile = File(...),
    source_csv_path: str = Form(""),
    dry_run: bool = Form(False),
    session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> MentorImportResponse:
    filename = file.filename or "mentors.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported for mentor import")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    report = MENTOR_STORE.import_csv_bytes(
        content,
        source_csv_path=(source_csv_path.strip() or filename),
        actor=session.username,
        dry_run=dry_run,
    )
    return MentorImportResponse(**report)


@app.get("/mentors/export-csv")
def export_mentors_csv(
    include_inactive: bool = True,
    _session: AuthSession = Depends(_require_auth()),
) -> StreamingResponse:
    export_payload = MENTOR_STORE.export_csv(include_inactive=include_inactive)
    csv_text = str(export_payload["csv_text"])
    output = BytesIO(csv_text.encode("utf-8"))
    headers = {"Content-Disposition": "attachment; filename=mentor_real_export.csv"}
    return StreamingResponse(output, media_type="text/csv; charset=utf-8", headers=headers)


@app.get("/mentors/export-xlsx")
def export_mentors_xlsx(
    include_inactive: bool = True,
    _session: AuthSession = Depends(_require_auth()),
) -> StreamingResponse:
    export_payload = MENTOR_STORE.export_csv(include_inactive=include_inactive)
    csv_text = str(export_payload["csv_text"])
    columns = [str(item) for item in export_payload.get("columns", [])]
    reader = csv.DictReader(StringIO(csv_text))
    rows = [dict(row) for row in reader]
    frame = pd.DataFrame(rows, columns=columns if columns else None)

    output = BytesIO()
    frame.to_excel(output, index=False)
    output.seek(0)
    headers = {"Content-Disposition": "attachment; filename=mentor_real_export.xlsx"}
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.post("/mentors/sync-to-default-csv", response_model=MentorSyncResponse)
def sync_mentors_to_default_csv(
    include_inactive: bool = True,
    _session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> MentorSyncResponse:
    result = MENTOR_STORE.write_export_to_path(
        MENTOR_SOURCE_CSV_PATH,
        include_inactive=include_inactive,
    )
    return MentorSyncResponse(
        rows=int(result.get("rows", 0)),
        columns=[str(item) for item in result.get("columns", [])],
        output_path=_normalize_source_path_for_api(str(result.get("output_path", ""))),
        backup_path=_normalize_source_path_for_api(str(result.get("backup_path", "")), fallback=""),
    )


@app.get("/mentors/{mentor_id}", response_model=MentorRecord)
def get_mentor(
    mentor_id: str,
    _session: AuthSession = Depends(_require_auth()),
) -> MentorRecord:
    record = MENTOR_STORE.get_by_id(mentor_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Mentor '{mentor_id}' was not found")
    return MentorRecord(**_mentor_record_for_api(record))


@app.post("/mentors", response_model=MentorRecord)
def create_mentor(
    request: MentorCreateRequest,
    session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> MentorRecord:
    payload = _model_dict(request, exclude_unset=False)
    if not str(payload.get("source_csv_path", "")).strip():
        payload["source_csv_path"] = str(MENTOR_SOURCE_CSV_PATH)
    try:
        created = MENTOR_STORE.create(payload, actor=session.username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MentorRecord(**_mentor_record_for_api(created))


@app.put("/mentors/{mentor_id}", response_model=MentorRecord)
def update_mentor(
    mentor_id: str,
    request: MentorUpdateRequest,
    session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> MentorRecord:
    updates = _model_dict(request, exclude_unset=True)
    if not updates:
        existing = MENTOR_STORE.get_by_id(mentor_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Mentor '{mentor_id}' was not found")
        return MentorRecord(**_mentor_record_for_api(existing))

    try:
        updated = MENTOR_STORE.update(mentor_id, updates, actor=session.username)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MentorRecord(**_mentor_record_for_api(updated))


@app.delete("/mentors/{mentor_id}", response_model=MentorRecord)
def deactivate_mentor(
    mentor_id: str,
    session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> MentorRecord:
    try:
        updated = MENTOR_STORE.deactivate(mentor_id, actor=session.username)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MentorRecord(**_mentor_record_for_api(updated))


@app.post("/mentors/bulk-delete", response_model=MentorBulkDeleteResponse)
def bulk_delete_mentors(
    request: MentorBulkDeleteRequest,
    _session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> MentorBulkDeleteResponse:
    result = MENTOR_STORE.delete_many(request.mentor_ids)
    return MentorBulkDeleteResponse(
        requested=int(result.get("requested", 0)),
        deleted=int(result.get("deleted", 0)),
        deleted_mentor_ids=[str(item) for item in result.get("deleted_mentor_ids", [])],
        not_found_mentor_ids=[str(item) for item in result.get("not_found_mentor_ids", [])],
    )


@app.get("/mentors/linkedin-enrichment/config", response_model=LinkedInEnrichmentConfigResponse)
def get_linkedin_enrichment_config(
    _session: AuthSession = Depends(_require_auth()),
) -> LinkedInEnrichmentConfigResponse:
    config = LINKEDIN_ENRICHMENT.config()
    return LinkedInEnrichmentConfigResponse(
        enabled=config.get("enabled") == True,
        provider=str(config.get("provider", "")),
        disabled_reason=str(config.get("disabled_reason", "")),
        min_interval_seconds=int(config.get("min_interval_seconds", 0)),
    )


@app.post("/mentors/{mentor_id}/enrich-linkedin", response_model=MentorEnrichmentResponse)
def enqueue_linkedin_enrichment(
    mentor_id: str,
    session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> MentorEnrichmentResponse:
    record = MENTOR_STORE.get_by_id(mentor_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Mentor '{mentor_id}' was not found")
    mentor_name = (
        str(record.get("full_name", "")).strip()
        or " ".join(
            part for part in [str(record.get("first_name", "")).strip(), str(record.get("last_name", "")).strip()] if part
        ).strip()
        or mentor_id
    )
    raw_linkedin_url, normalized_linkedin_url, linkedin_source, raw_linkedin_fields = _resolve_record_linkedin_url(
        record
    )
    LOG.info(
        "linkedin_enrichment_url_resolution mentor_id=%s mentor_name=%s raw_fields=%s selected_source=%s selected_raw=%s normalized_url=%s",
        mentor_id,
        mentor_name,
        raw_linkedin_fields,
        linkedin_source,
        raw_linkedin_url,
        normalized_linkedin_url,
    )

    if not raw_linkedin_url:
        return MentorEnrichmentResponse(
            mentor_id=mentor_id,
            enrichment_status="failed",
            message="No LinkedIn URL is saved for this mentor.",
            updated_fields=[],
            mentor=MentorRecord(**_mentor_record_for_api(record)),
        )

    linkedin_url_for_enrichment = normalized_linkedin_url or raw_linkedin_url
    if normalized_linkedin_url and str(record.get("linkedin_url", "")).strip() != normalized_linkedin_url:
        record = MENTOR_STORE.update(
            mentor_id,
            {"linkedin_url": normalized_linkedin_url},
            actor=session.username,
        )

    LOG.info(
        "linkedin_enrichment_attempt mentor_id=%s mentor_name=%s actor=%s provider=%s linkedin_url=%s",
        mentor_id,
        mentor_name,
        session.username,
        LINKEDIN_ENRICHMENT.provider_name,
        linkedin_url_for_enrichment,
    )
    result = LINKEDIN_ENRICHMENT.enrich_for_mentor(mentor_id, linkedin_url_for_enrichment)
    allowed_updates = {
        key: value
        for key, value in result.updates.items()
        if str(value).strip()
        and key
        in {
            "profile_photo_url",
            "current_company",
            "current_job_title",
            "current_location",
            "current_city",
            "current_state",
        }
    }

    def _normalize_for_compare(value: Any) -> str:
        return str(value or "").strip().lower()

    changed_updates = {
        key: value
        for key, value in allowed_updates.items()
        if _normalize_for_compare(value) != _normalize_for_compare(record.get(key))
    }

    fallback_updates: Dict[str, str] = {}
    fallback_changed_updates: Dict[str, str] = {}
    if not changed_updates:
        fallback_updates = _lookup_canonical_mentor_profile_fallback(record)
        fallback_changed_updates = {
            key: value
            for key, value in fallback_updates.items()
            if _normalize_for_compare(value) != _normalize_for_compare(record.get(key))
        }

        existing_photo = str(record.get("profile_photo_url", "")).strip()
        if (
            not fallback_updates.get("profile_photo_url")
            and not allowed_updates.get("profile_photo_url")
            and "ui-avatars.com/api/" in existing_photo
        ):
            fallback_changed_updates["profile_photo_url"] = ""

    normalized_url = str((result.provider_metadata or {}).get("normalized_url", "")).strip()
    LOG.info(
        "linkedin_enrichment_mapping mentor_id=%s mentor_name=%s provider=%s status=%s normalized_url=%s extracted_fields=%s changed_fields=%s",
        mentor_id,
        mentor_name,
        LINKEDIN_ENRICHMENT.provider_name,
        result.status,
        normalized_url,
        sorted(allowed_updates.keys()),
        sorted(changed_updates.keys()),
    )

    if fallback_changed_updates:
        LOG.info(
            "linkedin_enrichment_csv_fallback mentor_id=%s mentor_name=%s fallback_fields=%s",
            mentor_id,
            mentor_name,
            sorted(fallback_changed_updates.keys()),
        )

    if result.status in {"success", "partial"} and changed_updates:
        changed_updates["last_enriched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        changed_updates["enrichment_status"] = result.status
        changed_updates["enrichment_provider_metadata"] = result.provider_metadata
        updated = MENTOR_STORE.update(mentor_id, changed_updates, actor=session.username)
        LOG.info(
            "linkedin_enrichment_success mentor_id=%s mentor_name=%s actor=%s status=%s updated_fields=%s",
            mentor_id,
            mentor_name,
            session.username,
            result.status,
            sorted(changed_updates.keys()),
        )
        return MentorEnrichmentResponse(
            mentor_id=mentor_id,
            enrichment_status=result.status,
            message=result.message,
            updated_fields=sorted(changed_updates.keys()),
            mentor=MentorRecord(**_mentor_record_for_api(updated)),
        )

    if fallback_changed_updates:
        fallback_changed_updates["last_enriched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        fallback_changed_updates["enrichment_status"] = "partial"
        fallback_metadata = dict(result.provider_metadata or {})
        fallback_metadata["fallback_source"] = str(MENTOR_SOURCE_CSV_PATH)
        fallback_changed_updates["enrichment_provider_metadata"] = fallback_metadata
        updated = MENTOR_STORE.update(mentor_id, fallback_changed_updates, actor=session.username)
        fallback_message = (
            "LinkedIn provider returned no usable profile fields; "
            "updated from canonical mentor profile fallback data."
        )
        return MentorEnrichmentResponse(
            mentor_id=mentor_id,
            enrichment_status="partial",
            message=fallback_message,
            updated_fields=sorted(fallback_changed_updates.keys()),
            mentor=MentorRecord(**_mentor_record_for_api(updated)),
        )

    if result.status in {"success", "partial"} and not allowed_updates:
        message = (
            "LinkedIn enrichment completed, but no usable profile fields were returned for this URL."
        )
    elif result.status in {"success", "partial"} and not changed_updates:
        message = "LinkedIn enrichment completed, but no profile fields changed."
    else:
        message = result.message

    LOG.warning(
        "linkedin_enrichment_failed mentor_id=%s mentor_name=%s actor=%s status=%s extracted_fields=%s changed_fields=%s message=%s",
        mentor_id,
        mentor_name,
        session.username,
        result.status,
        sorted(allowed_updates.keys()),
        sorted(changed_updates.keys()),
        message,
    )
    return MentorEnrichmentResponse(
        mentor_id=mentor_id,
        enrichment_status="failed" if result.status in {"success", "partial"} else result.status,
        message=message,
        updated_fields=[],
        mentor=MentorRecord(**_mentor_record_for_api(record)),
    )


@app.post("/run_match")
async def run_match(
    mentee_file: UploadFile = File(...),
    mentor_file: Optional[UploadFile] = File(None),
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
        mentor_source = "manager_store"

        _as_csv(mentee_file.filename or "mentees.csv", await mentee_file.read(), mentee_csv)
        mentor_payload: Optional[bytes] = None
        mentor_filename = "mentors.csv"
        if mentor_file is not None:
            mentor_payload = await mentor_file.read()
            mentor_filename = mentor_file.filename or mentor_filename

        if mentor_payload:
            _as_csv(mentor_filename, mentor_payload, mentor_csv)
            mentor_source = "uploaded_file"
        else:
            export_payload = MENTOR_STORE.export_csv(include_inactive=False)
            if int(export_payload.get("rows", 0)) <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="No active mentors are available in Mentor Manager. Add mentors before running matching.",
                )
            mentor_csv.write_text(str(export_payload.get("csv_text", "")), encoding="utf-8")
            mentor_source = "mentor_manager"

        mentor_capacities = _extract_mentor_capacity_map(mentor_csv)
        state_payload = _state_dict(payload)
        state_path.write_text(json.dumps(state_payload, indent=2), encoding="utf-8")
        try:
            MATCHING_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            MATCHING_STATE_PATH.write_text(json.dumps(state_payload, indent=2), encoding="utf-8")
        except Exception as exc:
            LOG.warning("state_mirror_write_failed path=%s error=%s", MATCHING_STATE_PATH, exc)

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
        if isinstance(result, dict):
            _attach_mentor_capacity_metadata(result, mentor_capacities)
        return {
            "status": "ok",
            "result": result,
            "stdout": completed.stdout,
            "mentor_source": mentor_source,
        }


@app.post("/update_orgs")
def update_orgs(
    request: ScriptRequest,
    _session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> Dict[str, Any]:
    _audit_dev_action("update_orgs", _session)
    if request.script_path:
        script_path = Path(request.script_path).expanduser()
        try:
            result = _run_script_with_output_fallback(script_path, ORGS_PATH)
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            if _is_timeout_script_failure(detail):
                result = _timeout_degraded_result(script_path=script_path, detail=detail)
            else:
                raise
        result["file"] = _read_text_file(ORGS_PATH)
        return result

    for candidate in _script_candidates("orgs"):
        if candidate.exists():
            try:
                result = _run_script_with_output_fallback(candidate, ORGS_PATH)
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, dict) else {}
                if _is_timeout_script_failure(detail):
                    result = _timeout_degraded_result(script_path=candidate, detail=detail)
                else:
                    raise
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
        script_path = Path(request.script_path).expanduser()
        try:
            result = _run_script_with_output_fallback(
                script_path,
                CONCENTRATIONS_PATH,
            )
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            if _is_timeout_script_failure(detail):
                result = _timeout_degraded_result(script_path=script_path, detail=detail)
            else:
                raise
        result["file"] = _read_text_file(CONCENTRATIONS_PATH)
        return result

    for candidate in _script_candidates("concentrations"):
        if candidate.exists():
            try:
                result = _run_script_with_output_fallback(candidate, CONCENTRATIONS_PATH)
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, dict) else {}
                if _is_timeout_script_failure(detail):
                    result = _timeout_degraded_result(script_path=candidate, detail=detail)
                else:
                    raise
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
    backup_path = _backup_current_file(output_path, request.file_key)
    for candidate in _script_candidates(str(script_kind)):
        if candidate.exists():
            try:
                result = _run_script_with_output_fallback(candidate, output_path)
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, dict) else {}
                if _is_timeout_script_failure(detail):
                    result = _timeout_degraded_result(script_path=candidate, detail=detail)
                else:
                    raise
            result["file"] = _read_text_file(output_path)
            result["file_key"] = request.file_key
            result["label"] = str(entry["label"])
            result["backup_path"] = (
                _normalize_repo_path_for_api(str(backup_path), fallback="")
                if backup_path
                else None
            )
            return result

    raise HTTPException(status_code=404, detail=f"No update script found for {request.file_key}")


@app.get("/dev/matching-state")
def get_dev_matching_state(
    _session: AuthSession = Depends(_require_auth(require_dev=True)),
) -> Dict[str, Any]:
    _audit_dev_action("get_dev_matching_state", _session)
    return _load_matching_state_for_api(MATCHING_STATE_PATH)


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
