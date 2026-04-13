from __future__ import annotations

import copy
import csv
from dataclasses import dataclass
from io import BytesIO, StringIO
import json
import logging
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from .linkedin_enrichment import normalize_linkedin_profile_url

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except Exception:  # pragma: no cover - optional until postgres mode is used
    psycopg = None
    dict_row = None
    Jsonb = None


BACKEND_ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger("wrapper.mentor_store")


class MentorStoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class MentorStoreStatus:
    mode: str
    durable: bool
    description: str
    database_configured: bool = False
    database_url_present: bool = False
    store_path: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "durable": self.durable,
            "description": self.description,
            "database_configured": self.database_configured,
            "database_url_present": self.database_url_present,
            "store_path": self.store_path,
        }


@dataclass
class ParsedImportRow:
    row_index: int
    row: Dict[str, Any]


def _resolve_from_backend(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path.resolve()


DEFAULT_MENTOR_STORE_PATH = Path(
    os.getenv(
        "WRAPPER_MENTOR_STORE_PATH",
        str(BACKEND_ROOT / "data" / "mentors" / "mentors_store.json"),
    )
)
DEFAULT_MENTOR_STORE_PATH = _resolve_from_backend(str(DEFAULT_MENTOR_STORE_PATH))
DEFAULT_MENTOR_BACKUP_DIR = Path(
    os.getenv(
        "WRAPPER_MENTOR_BACKUP_DIR",
        str(BACKEND_ROOT / "data" / "mentors" / "backups"),
    )
)
DEFAULT_MENTOR_BACKUP_DIR = _resolve_from_backend(str(DEFAULT_MENTOR_BACKUP_DIR))

IMMUTABLE_FIELDS = {
    "mentor_id",
}

MENTOR_FIELDS = {
    "mentor_id",
    "email",
    "first_name",
    "last_name",
    "full_name",
    "linkedin_url",
    "profile_photo_url",
    "current_company",
    "current_job_title",
    "current_location",
    "current_city",
    "current_state",
    "degrees_text",
    "industry_focus_area",
    "professional_experience",
    "about_yourself",
    "students_interested",
    "phone",
    "preferred_contact_method",
    "is_active",
    "source_csv_path",
    "source_timestamp",
    "last_modified_at",
    "last_modified_by",
    "last_enriched_at",
    "enrichment_status",
    "enrichment_provider_metadata",
    "extra_fields",
}

DB_COLUMNS: Sequence[str] = (
    "mentor_id",
    "email",
    "first_name",
    "last_name",
    "full_name",
    "linkedin_url",
    "profile_photo_url",
    "current_company",
    "current_job_title",
    "current_location",
    "current_city",
    "current_state",
    "degrees_text",
    "industry_focus_area",
    "professional_experience",
    "about_yourself",
    "students_interested",
    "phone",
    "preferred_contact_method",
    "is_active",
    "source_csv_path",
    "source_timestamp",
    "last_modified_at",
    "last_modified_by",
    "last_enriched_at",
    "enrichment_status",
    "enrichment_provider_metadata",
    "extra_fields",
    "normalized_email",
    "normalized_full_name",
)


CSV_BASE_COLUMNS: List[str] = [
    "Timestamp",
    "Email",
    "LinkedIn",
    "First Name",
    "Last Name",
    "Pronouns",
    "Degrees",
    "Current City",
    "Current State",
    "Current City State",
    "Current Job Title",
    "Current Company",
    "Previous Mentorship",
    "Industry Focus Area",
    "Previous Involvement",
    "Previous Involvement Organizations",
    "Why Interested",
    "Professional Experience",
    "About Yourself",
    "Students Interested",
]

CSV_MANAGED_COLUMNS: List[str] = [
    "Profile Photo URL",
    "Phone",
    "Preferred Contact Method",
    "Is Active",
    "Mentor ID",
    "Last Modified At",
    "Last Modified By",
    "Last Enriched At",
    "Enrichment Status",
]

CSV_IMPORT_FIELD_BY_HEADER = {
    "timestamp": "source_timestamp",
    "email": "email",
    "linkedin": "linkedin_url",
    "linkedin url": "linkedin_url",
    "first name": "first_name",
    "last name": "last_name",
    "profile photo url": "profile_photo_url",
    "degrees": "degrees_text",
    "current city": "current_city",
    "current state": "current_state",
    "current city state": "current_location",
    "current location": "current_location",
    "current job title": "current_job_title",
    "current company": "current_company",
    "industry focus area": "industry_focus_area",
    "professional experience": "professional_experience",
    "about yourself": "about_yourself",
    "students interested": "students_interested",
    "phone": "phone",
    "preferred contact method": "preferred_contact_method",
    "is active": "is_active",
    "mentor id": "mentor_id",
    "last modified at": "last_modified_at",
    "last modified by": "last_modified_by",
    "last enriched at": "last_enriched_at",
    "enrichment status": "enrichment_status",
}

LINKEDIN_RECORD_ALIAS_KEYS: List[str] = [
    "linkedin_url",
    "linkedin",
    "linkedinUrl",
    "linkedinURL",
    "profile_link",
    "profileLink",
    "profile_url",
    "profileUrl",
    "profile_link_url",
    "profileLinkUrl",
    "profile",
]

LINKEDIN_EXTRA_FIELD_HEADERS = {
    "linkedin",
    "linkedin url",
    "linkedin_url",
    "linkedin profile",
    "linkedin profile url",
    "linkedin url / profile",
    "profile link",
    "profile url",
    "linkedin profile link",
}


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_header(value: str) -> str:
    lowered = (value or "").strip().lower()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_email(value: Any) -> str:
    return _normalize_whitespace(_stringify(value)).lower()


def _normalize_name(value: Any) -> str:
    return _normalize_whitespace(_stringify(value)).lower()


def _normalize_field(field: str, value: Any) -> Any:
    if field in {"students_interested"}:
        if value is None:
            return 0
        text = _stringify(value)
        if not text:
            return 0
        match = re.search(r"(\d+)", text)
        if not match:
            return 0
        return int(match.group(1))

    if field in {"is_active"}:
        if isinstance(value, bool):
            return value
        text = _stringify(value).lower()
        if text in {"", "none", "null"}:
            return True
        return text in {"1", "true", "yes", "y", "active"}

    if field in {"extra_fields", "enrichment_provider_metadata"}:
        return value if isinstance(value, dict) else {}

    if value is None:
        return ""
    return _stringify(value)


def _normalize_linkedin_profile(raw_value: Any) -> str:
    text = _stringify(raw_value)
    if not text:
        return ""
    normalized, error = normalize_linkedin_profile_url(text)
    if not error and normalized:
        return normalized
    if "linkedin.com/in/" in text.lower() or "linkedin.com/pub/" in text.lower():
        if not text.startswith(("http://", "https://")):
            return f"https://{text}"
        return text
    return ""


def _extract_canonical_linkedin_url(record: Dict[str, Any], *, extra_fields: Dict[str, Any]) -> str:
    candidates: List[str] = []

    def _append_candidate(value: Any) -> None:
        text = _stringify(value)
        if text and text not in candidates:
            candidates.append(text)

    for key in LINKEDIN_RECORD_ALIAS_KEYS:
        _append_candidate(record.get(key))

    for key, value in extra_fields.items():
        if _normalize_header(str(key)) in LINKEDIN_EXTRA_FIELD_HEADERS:
            _append_candidate(value)

    for candidate in candidates:
        normalized = _normalize_linkedin_profile(candidate)
        if normalized:
            return normalized
    return ""


def _extra_value(extras: Dict[str, Any], candidates: List[str]) -> str:
    for key in candidates:
        if key in extras and _stringify(extras.get(key)):
            return _stringify(extras.get(key))
    for key, value in extras.items():
        norm_key = _normalize_header(str(key))
        for candidate in candidates:
            if norm_key == _normalize_header(candidate) and _stringify(value):
                return _stringify(value)
    return ""


def _json_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True)


class MentorStoreCommon:
    @property
    def mode(self) -> str:
        raise NotImplementedError

    def status(self) -> MentorStoreStatus:
        raise NotImplementedError

    def load_records(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_by_id(self, mentor_id: str) -> Optional[Dict[str, Any]]:
        target = _stringify(mentor_id)
        if not target:
            return None
        for record in self.load_records():
            if _stringify(record.get("mentor_id")) == target:
                return record
        return None

    def create(self, payload: Dict[str, Any], *, actor: str) -> Dict[str, Any]:
        base = self._normalize_record(payload)
        duplicate = self._find_duplicate_record(self.load_records(), base)
        if duplicate is not None:
            raise ValueError(self._duplicate_error_message(duplicate))

        if not base.get("mentor_id"):
            base["mentor_id"] = self._generate_mentor_id(base)
        now_iso = _now_iso()
        base["last_modified_at"] = now_iso
        base["last_modified_by"] = actor
        if not base.get("source_timestamp"):
            base["source_timestamp"] = now_iso
        created = self._normalize_record(base)
        self._insert_many([created])
        return copy.deepcopy(created)

    def update(self, mentor_id: str, updates: Dict[str, Any], *, actor: str) -> Dict[str, Any]:
        target = _stringify(mentor_id)
        if not target:
            raise ValueError("mentor_id is required")

        existing = self.get_by_id(target)
        if existing is None:
            raise KeyError(f"Mentor '{mentor_id}' was not found")

        merged = copy.deepcopy(existing)
        for key, value in updates.items():
            if key in IMMUTABLE_FIELDS:
                continue
            merged[key] = value
        merged = self._normalize_record(merged)
        merged["mentor_id"] = target
        merged["last_modified_at"] = _now_iso()
        merged["last_modified_by"] = actor

        duplicate = self._find_duplicate_record(
            self.load_records(),
            merged,
            exclude_mentor_id=target,
        )
        if duplicate is not None:
            raise ValueError(self._duplicate_error_message(duplicate))

        self._update_record(merged)
        return copy.deepcopy(merged)

    def deactivate(self, mentor_id: str, *, actor: str) -> Dict[str, Any]:
        return self.update(mentor_id, {"is_active": False}, actor=actor)

    def delete_many(self, mentor_ids: List[str]) -> Dict[str, Any]:
        targets: List[str] = []
        seen: set[str] = set()
        for mentor_id in mentor_ids:
            normalized = _stringify(mentor_id)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            targets.append(normalized)

        if not targets:
            return {
                "requested": 0,
                "deleted": 0,
                "deleted_mentor_ids": [],
                "not_found_mentor_ids": [],
            }

        existing_ids = {
            _stringify(record.get("mentor_id"))
            for record in self.load_records()
            if _stringify(record.get("mentor_id"))
        }
        deleted_ids = [mentor_id for mentor_id in targets if mentor_id in existing_ids]
        if deleted_ids:
            self._delete_many_ids(deleted_ids)
        not_found = [mentor_id for mentor_id in targets if mentor_id not in existing_ids]
        return {
            "requested": len(targets),
            "deleted": len(deleted_ids),
            "deleted_mentor_ids": deleted_ids,
            "not_found_mentor_ids": not_found,
        }

    def import_tabular_bytes(
        self,
        content: bytes,
        *,
        filename: str,
        source_csv_path: str,
        actor: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        rows = _parse_tabular_rows(content, filename)
        existing_records = self.load_records()
        known_records = [copy.deepcopy(record) for record in existing_records]

        summary: Dict[str, Any] = {
            "rows_read": len(rows),
            "added": 0,
            "skipped_duplicates": 0,
            "invalid": 0,
            "errors": 0,
            "duplicate_rows": [],
            "invalid_rows": [],
            "error_rows": [],
        }

        records_to_add: List[Dict[str, Any]] = []
        for parsed in rows:
            try:
                incoming = self._record_from_csv_row(
                    parsed.row,
                    source_csv_path=source_csv_path,
                )
                validation_error = self._validate_import_identity(incoming)
                if validation_error:
                    summary["invalid"] += 1
                    summary["invalid_rows"].append(
                        {"row_index": parsed.row_index, "reason": validation_error}
                    )
                    continue

                duplicate = self._find_duplicate_record(known_records, incoming)
                if duplicate is not None:
                    summary["skipped_duplicates"] += 1
                    summary["duplicate_rows"].append(
                        self._duplicate_row_detail(parsed.row_index, duplicate)
                    )
                    continue

                if not incoming.get("mentor_id"):
                    incoming["mentor_id"] = self._generate_mentor_id(incoming)
                now_iso = _now_iso()
                incoming["last_modified_at"] = now_iso
                incoming["last_modified_by"] = actor
                if not incoming.get("source_timestamp"):
                    incoming["source_timestamp"] = now_iso
                normalized = self._normalize_record(incoming)
                records_to_add.append(normalized)
                known_records.append(copy.deepcopy(normalized))
                summary["added"] += 1
            except Exception as exc:  # pragma: no cover - malformed input defense
                summary["errors"] += 1
                summary["error_rows"].append(
                    {"row_index": parsed.row_index, "error": str(exc)}
                )

        if records_to_add and not dry_run:
            self._insert_many(records_to_add)

        return summary

    def export_csv(
        self,
        *,
        include_inactive: bool = True,
    ) -> Dict[str, Any]:
        records = self.load_records()
        filtered = [
            row for row in records if include_inactive or bool(row.get("is_active", True))
        ]
        filtered.sort(key=lambda row: _stringify(row.get("full_name")).lower())

        extra_columns: List[str] = []
        seen_extra = set()
        for record in filtered:
            extras = record.get("extra_fields", {})
            if not isinstance(extras, dict):
                continue
            for key in extras:
                if not key:
                    continue
                if key in CSV_BASE_COLUMNS or key in CSV_MANAGED_COLUMNS:
                    continue
                if key in seen_extra:
                    continue
                seen_extra.add(key)
                extra_columns.append(key)
        extra_columns.sort(key=lambda item: item.lower())

        columns = CSV_BASE_COLUMNS + CSV_MANAGED_COLUMNS + extra_columns
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for record in filtered:
            writer.writerow(self._csv_row_from_record(record, extra_columns=extra_columns))

        return {
            "columns": columns,
            "rows": len(filtered),
            "csv_text": output.getvalue(),
        }

    def write_export_to_path(
        self,
        path: Path,
        *,
        include_inactive: bool = True,
    ) -> Dict[str, Any]:
        export_payload = self.export_csv(include_inactive=include_inactive)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        text = str(export_payload["csv_text"]).replace("\r\n", "\n")

        backup_path: Optional[Path] = None
        if target.exists():
            timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            backup_dir = target.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"{target.stem}_{timestamp}{target.suffix or '.csv'}"
            shutil.copy2(target, backup_path)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=str(target.parent),
            prefix="mentor_export_",
            suffix=".tmp",
        ) as tmp_file:
            tmp_file.write(text)
            tmp_file.flush()
            temp_path = Path(tmp_file.name)
        temp_path.replace(target)

        return {
            "rows": export_payload["rows"],
            "columns": export_payload["columns"],
            "output_path": str(target),
            "backup_path": str(backup_path) if backup_path else None,
        }

    def migrate_from_file_store(
        self,
        source_path: Path,
        *,
        actor: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        payload_path = Path(source_path).expanduser().resolve()
        if not payload_path.exists():
            raise FileNotFoundError(f"Mentor store file not found: {payload_path}")
        try:
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"Could not read mentor store payload: {exc}") from exc

        records = payload.get("records", []) if isinstance(payload, dict) else []
        rows: List[ParsedImportRow] = []
        for index, row in enumerate(records, start=1):
            if isinstance(row, dict):
                rows.append(ParsedImportRow(row_index=index, row=row))

        existing_records = self.load_records()
        known_records = [copy.deepcopy(record) for record in existing_records]
        summary: Dict[str, Any] = {
            "source_path": str(payload_path),
            "rows_read": len(rows),
            "added": 0,
            "skipped_duplicates": 0,
            "invalid": 0,
            "errors": 0,
            "duplicate_rows": [],
            "invalid_rows": [],
            "error_rows": [],
        }
        records_to_add: List[Dict[str, Any]] = []

        for parsed in rows:
            try:
                normalized = self._normalize_record(parsed.row)
                validation_error = self._validate_import_identity(normalized)
                if validation_error:
                    summary["invalid"] += 1
                    summary["invalid_rows"].append(
                        {"row_index": parsed.row_index, "reason": validation_error}
                    )
                    continue
                duplicate = self._find_duplicate_record(known_records, normalized)
                if duplicate is not None:
                    summary["skipped_duplicates"] += 1
                    summary["duplicate_rows"].append(
                        self._duplicate_row_detail(parsed.row_index, duplicate)
                    )
                    continue
                if not normalized.get("last_modified_at"):
                    normalized["last_modified_at"] = _now_iso()
                if not normalized.get("last_modified_by"):
                    normalized["last_modified_by"] = actor
                records_to_add.append(normalized)
                known_records.append(copy.deepcopy(normalized))
                summary["added"] += 1
            except Exception as exc:  # pragma: no cover
                summary["errors"] += 1
                summary["error_rows"].append(
                    {"row_index": parsed.row_index, "error": str(exc)}
                )

        if records_to_add and not dry_run:
            self._insert_many(records_to_add)
        return summary

    def _normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        base: Dict[str, Any] = {}
        for key in MENTOR_FIELDS:
            base[key] = _normalize_field(key, record.get(key))

        if not base.get("mentor_id"):
            base["mentor_id"] = self._generate_mentor_id(base)

        base["full_name"] = self._derive_full_name(
            first_name=_stringify(base.get("first_name")),
            last_name=_stringify(base.get("last_name")),
            fallback=_stringify(base.get("full_name")),
            email=_stringify(base.get("email")),
        )

        incoming_extra = record.get("extra_fields")
        extra: Dict[str, Any] = {}
        if isinstance(incoming_extra, dict):
            extra.update(incoming_extra)

        for key, value in record.items():
            if key in MENTOR_FIELDS:
                continue
            extra[key] = value

        base["linkedin_url"] = _extract_canonical_linkedin_url(record, extra_fields=extra)
        base["extra_fields"] = {
            key: value
            for key, value in extra.items()
            if _normalize_header(str(key)) not in LINKEDIN_EXTRA_FIELD_HEADERS
        }

        if not _stringify(base.get("source_csv_path")):
            base["source_csv_path"] = "mentor_manager"

        return base

    def _record_from_csv_row(self, row: Dict[str, Any], *, source_csv_path: str) -> Dict[str, Any]:
        extra_fields: Dict[str, Any] = {}
        mapped: Dict[str, Any] = {
            "source_csv_path": source_csv_path or "mentor_import",
            "is_active": True,
        }

        for original_key, value in row.items():
            clean_key = _stringify(original_key)
            if not clean_key:
                continue
            normalized_key = _normalize_header(clean_key)
            mapped_field = CSV_IMPORT_FIELD_BY_HEADER.get(normalized_key)
            if mapped_field:
                mapped[mapped_field] = value
            else:
                extra_fields[clean_key] = value

        timestamp = mapped.get("source_timestamp")
        if not _stringify(timestamp):
            timestamp = row.get("Timestamp", "") or row.get("timestamp", "")
        mapped["source_timestamp"] = _stringify(timestamp)
        mapped["extra_fields"] = extra_fields
        return self._normalize_record(mapped)

    def _validate_import_identity(self, record: Dict[str, Any]) -> str:
        if self._normalized_email(record):
            return ""
        raw_full_name = _normalize_name(record.get("full_name"))
        raw_first_name = _normalize_name(record.get("first_name"))
        raw_last_name = _normalize_name(record.get("last_name"))
        if raw_full_name and raw_full_name != "unknown mentor":
            return ""
        if raw_first_name or raw_last_name:
            return ""
        return "Row is missing both a usable email and full name."

    def _find_duplicate_record(
        self,
        records: Iterable[Dict[str, Any]],
        incoming: Dict[str, Any],
        *,
        exclude_mentor_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        incoming_email = self._normalized_email(incoming)
        incoming_name = self._normalized_full_name(incoming)
        exclude = _stringify(exclude_mentor_id)

        if incoming_email:
            for record in records:
                if exclude and _stringify(record.get("mentor_id")) == exclude:
                    continue
                if self._normalized_email(record) == incoming_email:
                    return {
                        "reason": "duplicate_email",
                        "matched_record": record,
                    }
            return None

        if incoming_name:
            for record in records:
                if exclude and _stringify(record.get("mentor_id")) == exclude:
                    continue
                if self._normalized_full_name(record) == incoming_name:
                    return {
                        "reason": "duplicate_name",
                        "matched_record": record,
                    }
        return None

    def _duplicate_row_detail(
        self,
        row_index: int,
        duplicate: Dict[str, Any],
    ) -> Dict[str, Any]:
        matched = duplicate.get("matched_record", {}) if isinstance(duplicate, dict) else {}
        reason = _stringify(duplicate.get("reason")) if isinstance(duplicate, dict) else "duplicate"
        return {
            "row_index": row_index,
            "reason": reason,
            "matched_mentor_id": _stringify(matched.get("mentor_id")),
            "matched_email": _stringify(matched.get("email")),
            "matched_name": _stringify(matched.get("full_name")),
        }

    def _duplicate_error_message(self, duplicate: Dict[str, Any]) -> str:
        reason = _stringify(duplicate.get("reason"))
        matched = duplicate.get("matched_record", {}) if isinstance(duplicate, dict) else {}
        label = _stringify(matched.get("email")) or _stringify(matched.get("full_name")) or _stringify(matched.get("mentor_id"))
        if reason == "duplicate_email":
            return f"Mentor with this email already exists: {label}"
        if reason == "duplicate_name":
            return f"Mentor with this normalized name already exists: {label}"
        return f"Duplicate mentor record: {label}"

    def _normalized_email(self, record: Dict[str, Any]) -> str:
        return _normalize_email(record.get("email"))

    def _normalized_full_name(self, record: Dict[str, Any]) -> str:
        full_name = _stringify(record.get("full_name"))
        if full_name:
            return _normalize_name(full_name)
        first = _stringify(record.get("first_name"))
        last = _stringify(record.get("last_name"))
        return _normalize_name(" ".join(part for part in [first, last] if part))

    def _csv_row_from_record(self, record: Dict[str, Any], *, extra_columns: List[str]) -> Dict[str, Any]:
        extras = record.get("extra_fields")
        if not isinstance(extras, dict):
            extras = {}

        city = _stringify(record.get("current_city"))
        state = _stringify(record.get("current_state"))
        location = _stringify(record.get("current_location"))
        if not location:
            location = ", ".join(part for part in [city, state] if part)

        row = {
            "Timestamp": _stringify(record.get("source_timestamp")),
            "Email": _stringify(record.get("email")),
            "LinkedIn": _stringify(record.get("linkedin_url")),
            "First Name": _stringify(record.get("first_name")),
            "Last Name": _stringify(record.get("last_name")),
            "Pronouns": _extra_value(extras, ["Pronouns", "pronouns"]),
            "Degrees": _stringify(record.get("degrees_text")),
            "Current City": city,
            "Current State": state,
            "Current City State": location,
            "Current Job Title": _stringify(record.get("current_job_title")),
            "Current Company": _stringify(record.get("current_company")),
            "Previous Mentorship": _extra_value(extras, ["Previous Mentorship", "previous mentorship"]),
            "Industry Focus Area": _stringify(record.get("industry_focus_area")),
            "Previous Involvement": _extra_value(extras, ["Previous Involvement", "previous involvement"]),
            "Previous Involvement Organizations": _extra_value(
                extras,
                [
                    "Previous Involvement Organizations",
                    "previous involvement organizations",
                ],
            ),
            "Why Interested": _extra_value(extras, ["Why Interested", "why interested"]),
            "Professional Experience": _stringify(record.get("professional_experience")),
            "About Yourself": _stringify(record.get("about_yourself")),
            "Students Interested": _stringify(record.get("students_interested")),
            "Profile Photo URL": _stringify(record.get("profile_photo_url")),
            "Phone": _stringify(record.get("phone")),
            "Preferred Contact Method": _stringify(record.get("preferred_contact_method")),
            "Is Active": "true" if bool(record.get("is_active", True)) else "false",
            "Mentor ID": _stringify(record.get("mentor_id")),
            "Last Modified At": _stringify(record.get("last_modified_at")),
            "Last Modified By": _stringify(record.get("last_modified_by")),
            "Last Enriched At": _stringify(record.get("last_enriched_at")),
            "Enrichment Status": _stringify(record.get("enrichment_status")),
        }
        for key in extra_columns:
            if key not in row:
                row[key] = _stringify(extras.get(key, ""))
        return row

    def _generate_mentor_id(self, record: Dict[str, Any]) -> str:
        email = _normalize_email(record.get("email"))
        if email:
            return email

        full_name = self._normalized_full_name(record)
        if full_name:
            slug = re.sub(r"[^a-z0-9]+", "-", full_name).strip("-")
            if slug:
                return slug

        linked_in = _stringify(record.get("linkedin_url")).lower()
        if linked_in:
            slug = re.sub(r"[^a-z0-9]+", "-", linked_in).strip("-")
            if slug:
                return slug
        return f"mentor-{int(time.time() * 1000)}"

    def _derive_full_name(self, *, first_name: str, last_name: str, fallback: str, email: str) -> str:
        name = " ".join(part for part in [first_name.strip(), last_name.strip()] if part).strip()
        if name:
            return name
        if fallback.strip():
            return fallback.strip()
        if email.strip():
            return email.strip()
        return "Unknown Mentor"

    def _insert_many(self, records: List[Dict[str, Any]]) -> None:
        raise NotImplementedError

    def _update_record(self, record: Dict[str, Any]) -> None:
        raise NotImplementedError

    def _delete_many_ids(self, mentor_ids: List[str]) -> None:
        raise NotImplementedError


class FileMentorStore(MentorStoreCommon):
    def __init__(self, *, store_path: Path, backup_dir: Path) -> None:
        requested_store_path = Path(store_path)
        requested_backup_dir = Path(backup_dir)
        self._store_path = requested_store_path
        self._backup_dir = requested_backup_dir

        try:
            self._ensure_storage_dirs(requested_store_path, requested_backup_dir)
            self._store_path = requested_store_path
            self._backup_dir = requested_backup_dir
        except OSError as exc:
            runtime_root = Path(
                os.getenv("WRAPPER_RUNTIME_DATA_DIR", "/tmp/nlp_matching_runtime")
            ).expanduser()
            runtime_store = runtime_root / "mentors" / "mentors_store.json"
            runtime_backup = runtime_root / "mentors" / "backups"
            self._ensure_storage_dirs(runtime_store, runtime_backup)
            if requested_store_path.exists() and not runtime_store.exists():
                try:
                    runtime_store.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(requested_store_path, runtime_store)
                except OSError as seed_exc:
                    LOG.warning(
                        "mentor_store_seed_failed source=%s target=%s error=%s",
                        requested_store_path,
                        runtime_store,
                        seed_exc,
                    )
            self._store_path = runtime_store
            self._backup_dir = runtime_backup
            LOG.warning(
                "mentor_store_runtime_fallback requested_store=%s requested_backup=%s runtime_store=%s runtime_backup=%s error=%s",
                requested_store_path,
                requested_backup_dir,
                runtime_store,
                runtime_backup,
                exc,
            )

    @property
    def mode(self) -> str:
        return "file"

    def status(self) -> MentorStoreStatus:
        return MentorStoreStatus(
            mode="file",
            durable=False,
            description="Local file-backed mentor store",
            store_path=str(self._store_path),
        )

    def load_records(self) -> List[Dict[str, Any]]:
        payload = self._read_payload()
        records = payload.get("records", [])
        if not isinstance(records, list):
            return []
        output: List[Dict[str, Any]] = []
        for row in records:
            if isinstance(row, dict):
                output.append(self._normalize_record(row))
        return output

    def _insert_many(self, records: List[Dict[str, Any]]) -> None:
        payload = self._read_payload()
        existing = payload.get("records", [])
        if not isinstance(existing, list):
            existing = []
        existing.extend(records)
        self._save_records(existing)

    def _update_record(self, record: Dict[str, Any]) -> None:
        records = self.load_records()
        updated = False
        for index, existing in enumerate(records):
            if _stringify(existing.get("mentor_id")) == _stringify(record.get("mentor_id")):
                records[index] = record
                updated = True
                break
        if not updated:
            raise KeyError(f"Mentor '{record.get('mentor_id')}' was not found")
        self._save_records(records)

    def _delete_many_ids(self, mentor_ids: List[str]) -> None:
        targets = set(mentor_ids)
        records = [
            record for record in self.load_records() if _stringify(record.get("mentor_id")) not in targets
        ]
        self._save_records(records)

    def _read_payload(self) -> Dict[str, Any]:
        if not self._store_path.exists():
            initial = {"schema_version": 1, "updated_at": _now_iso(), "records": []}
            self._atomic_write_payload(initial, create_backup=False)
            return initial
        try:
            raw = self._store_path.read_text(encoding="utf-8")
            parsed = json.loads(raw)
        except (json.JSONDecodeError, OSError):
            return {"schema_version": 1, "updated_at": _now_iso(), "records": []}
        if not isinstance(parsed, dict):
            return {"schema_version": 1, "updated_at": _now_iso(), "records": []}
        return parsed

    def _save_records(self, records: List[Dict[str, Any]]) -> None:
        payload = {"schema_version": 1, "updated_at": _now_iso(), "records": records}
        self._atomic_write_payload(payload, create_backup=True)

    def _atomic_write_payload(self, payload: Dict[str, Any], *, create_backup: bool) -> None:
        if create_backup and self._store_path.exists():
            self._create_backup_snapshot()
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=str(self._store_path.parent),
            prefix="mentors_store_",
            suffix=".tmp",
        ) as tmp_file:
            json.dump(payload, tmp_file, ensure_ascii=True, indent=2)
            tmp_file.flush()
            temp_path = Path(tmp_file.name)
        temp_path.replace(self._store_path)

    @staticmethod
    def _ensure_storage_dirs(store_path: Path, backup_dir: Path) -> None:
        store_path.parent.mkdir(parents=True, exist_ok=True)
        backup_dir.mkdir(parents=True, exist_ok=True)

    def _create_backup_snapshot(self) -> Optional[Path]:
        if not self._store_path.exists():
            return None
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        backup_path = self._backup_dir / f"{timestamp}.json"
        shutil.copy2(self._store_path, backup_path)
        return backup_path


class PostgresMentorStore(MentorStoreCommon):
    def __init__(self, *, database_url: str) -> None:
        if psycopg is None or dict_row is None or Jsonb is None:
            raise MentorStoreError(
                "psycopg is required for postgres mentor storage but is not installed."
            )
        self._database_url = _stringify(database_url)
        if not self._database_url:
            raise MentorStoreError(
                "WRAPPER_MENTOR_DATABASE_URL or DATABASE_URL must be set for postgres mentor storage."
            )
        self._ensure_schema()

    @property
    def mode(self) -> str:
        return "postgres"

    def status(self) -> MentorStoreStatus:
        return MentorStoreStatus(
            mode="postgres",
            durable=True,
            description="Postgres-backed mentor store",
            database_configured=True,
            database_url_present=bool(self._database_url),
        )

    def load_records(self) -> List[Dict[str, Any]]:
        sql = f"SELECT {', '.join(DB_COLUMNS)} FROM mentor_records ORDER BY lower(full_name), mentor_id"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        return [self._row_to_record(dict(row)) for row in rows]

    def _insert_many(self, records: List[Dict[str, Any]]) -> None:
        if not records:
            return
        sql = f"""
            INSERT INTO mentor_records (
                {', '.join(DB_COLUMNS)},
                created_at,
                updated_at
            ) VALUES (
                {', '.join(['%s'] * len(DB_COLUMNS))},
                NOW(),
                NOW()
            )
        """
        params = [self._record_params(record) for record in records]
        with self._connect() as conn, conn.cursor() as cur:
            cur.executemany(sql, params)
            conn.commit()

    def _update_record(self, record: Dict[str, Any]) -> None:
        assignments = [f"{column} = %s" for column in DB_COLUMNS if column != "mentor_id"]
        sql = f"""
            UPDATE mentor_records
            SET {', '.join(assignments)}, updated_at = NOW()
            WHERE mentor_id = %s
        """
        params = [
            self._record_value(record, column)
            for column in DB_COLUMNS
            if column != "mentor_id"
        ]
        params.append(_stringify(record.get("mentor_id")))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.rowcount <= 0:
                raise KeyError(f"Mentor '{record.get('mentor_id')}' was not found")
            conn.commit()

    def _delete_many_ids(self, mentor_ids: List[str]) -> None:
        if not mentor_ids:
            return
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM mentor_records WHERE mentor_id = ANY(%s)",
                (mentor_ids,),
            )
            conn.commit()

    def _record_params(self, record: Dict[str, Any]) -> Tuple[Any, ...]:
        return tuple(self._record_value(record, column) for column in DB_COLUMNS)

    def _record_value(self, record: Dict[str, Any], column: str) -> Any:
        if column == "normalized_email":
            return self._normalized_email(record)
        if column == "normalized_full_name":
            return self._normalized_full_name(record)
        value = record.get(column)
        if column in {"extra_fields", "enrichment_provider_metadata"}:
            return Jsonb(value if isinstance(value, dict) else {})
        return value

    def _row_to_record(self, row: Dict[str, Any]) -> Dict[str, Any]:
        record = {column: row.get(column) for column in DB_COLUMNS if column not in {"normalized_email", "normalized_full_name"}}
        return self._normalize_record(record)

    def _connect(self):
        return psycopg.connect(
            self._database_url,
            autocommit=False,
            row_factory=dict_row,
        )

    def _ensure_schema(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS mentor_records (
                mentor_id TEXT PRIMARY KEY,
                email TEXT NOT NULL DEFAULT '',
                first_name TEXT NOT NULL DEFAULT '',
                last_name TEXT NOT NULL DEFAULT '',
                full_name TEXT NOT NULL DEFAULT '',
                linkedin_url TEXT NOT NULL DEFAULT '',
                profile_photo_url TEXT NOT NULL DEFAULT '',
                current_company TEXT NOT NULL DEFAULT '',
                current_job_title TEXT NOT NULL DEFAULT '',
                current_location TEXT NOT NULL DEFAULT '',
                current_city TEXT NOT NULL DEFAULT '',
                current_state TEXT NOT NULL DEFAULT '',
                degrees_text TEXT NOT NULL DEFAULT '',
                industry_focus_area TEXT NOT NULL DEFAULT '',
                professional_experience TEXT NOT NULL DEFAULT '',
                about_yourself TEXT NOT NULL DEFAULT '',
                students_interested INTEGER NOT NULL DEFAULT 0,
                phone TEXT NOT NULL DEFAULT '',
                preferred_contact_method TEXT NOT NULL DEFAULT '',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                source_csv_path TEXT NOT NULL DEFAULT '',
                source_timestamp TEXT NOT NULL DEFAULT '',
                last_modified_at TEXT NOT NULL DEFAULT '',
                last_modified_by TEXT NOT NULL DEFAULT '',
                last_enriched_at TEXT NOT NULL DEFAULT '',
                enrichment_status TEXT NOT NULL DEFAULT '',
                enrichment_provider_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                extra_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
                normalized_email TEXT NOT NULL DEFAULT '',
                normalized_full_name TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS mentor_records_normalized_email_unique
                ON mentor_records (normalized_email)
                WHERE normalized_email <> ''
            """,
            """
            CREATE INDEX IF NOT EXISTS mentor_records_normalized_full_name_idx
                ON mentor_records (normalized_full_name)
            """,
        ]
        with self._connect() as conn, conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)
            conn.commit()


class MentorStore:
    def __init__(
        self,
        *,
        store_path: Path = DEFAULT_MENTOR_STORE_PATH,
        backup_dir: Path = DEFAULT_MENTOR_BACKUP_DIR,
        storage_mode: str = "",
        database_url: str = "",
        is_vercel: bool = False,
    ) -> None:
        resolved_mode = _stringify(storage_mode).lower()
        url = _stringify(database_url)
        if not resolved_mode:
            resolved_mode = "postgres" if (is_vercel or url) else "file"

        if resolved_mode not in {"file", "postgres"}:
            raise MentorStoreError(
                f"Unsupported mentor storage mode '{resolved_mode}'. Use 'file' or 'postgres'."
            )

        if is_vercel and resolved_mode != "postgres":
            raise MentorStoreError(
                "Vercel deployments require WRAPPER_MENTOR_STORAGE_MODE=postgres. "
                "File-backed mentor storage is not durable in production."
            )

        if resolved_mode == "postgres":
            self._backend: MentorStoreCommon = PostgresMentorStore(database_url=url)
        else:
            self._backend = FileMentorStore(store_path=store_path, backup_dir=backup_dir)

        status = self.status()
        LOG.info(
            "mentor_storage_initialized mode=%s durable=%s database_configured=%s store_path=%s",
            status.get("mode"),
            status.get("durable"),
            status.get("database_configured"),
            status.get("store_path"),
        )

    @property
    def mode(self) -> str:
        return self._backend.mode

    def status(self) -> Dict[str, Any]:
        return self._backend.status().as_dict()

    def load_records(self) -> List[Dict[str, Any]]:
        return self._backend.load_records()

    def get_by_id(self, mentor_id: str) -> Optional[Dict[str, Any]]:
        return self._backend.get_by_id(mentor_id)

    def create(self, payload: Dict[str, Any], *, actor: str) -> Dict[str, Any]:
        return self._backend.create(payload, actor=actor)

    def update(self, mentor_id: str, updates: Dict[str, Any], *, actor: str) -> Dict[str, Any]:
        return self._backend.update(mentor_id, updates, actor=actor)

    def deactivate(self, mentor_id: str, *, actor: str) -> Dict[str, Any]:
        return self._backend.deactivate(mentor_id, actor=actor)

    def delete_many(self, mentor_ids: List[str]) -> Dict[str, Any]:
        return self._backend.delete_many(mentor_ids)

    def import_tabular_bytes(
        self,
        content: bytes,
        *,
        filename: str,
        source_csv_path: str,
        actor: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        return self._backend.import_tabular_bytes(
            content,
            filename=filename,
            source_csv_path=source_csv_path,
            actor=actor,
            dry_run=dry_run,
        )

    def export_csv(self, *, include_inactive: bool = True) -> Dict[str, Any]:
        return self._backend.export_csv(include_inactive=include_inactive)

    def write_export_to_path(
        self,
        path: Path,
        *,
        include_inactive: bool = True,
    ) -> Dict[str, Any]:
        return self._backend.write_export_to_path(path, include_inactive=include_inactive)

    def migrate_from_file_store(
        self,
        source_path: Path,
        *,
        actor: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        if self.mode != "postgres":
            raise MentorStoreError("File-store migration is only available in postgres mentor storage mode.")
        return self._backend.migrate_from_file_store(source_path, actor=actor, dry_run=dry_run)


def _parse_tabular_rows(content: bytes, filename: str) -> List[ParsedImportRow]:
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        try:
            frame = pd.read_excel(BytesIO(content), dtype=str)
        except Exception as exc:
            raise ValueError(f"Could not read Excel file '{filename}': {exc}") from exc
        frame = frame.fillna("")
        frame.columns = [_stringify(column) for column in frame.columns]
        rows: List[ParsedImportRow] = []
        for row_index, row in enumerate(frame.to_dict(orient="records"), start=2):
            cleaned = {_stringify(key): value for key, value in row.items()}
            rows.append(ParsedImportRow(row_index=row_index, row=cleaned))
        return rows

    if suffix and suffix != ".csv":
        raise ValueError(f"Unsupported mentor import file '{filename}'. Use CSV or Excel.")

    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(StringIO(text))
    rows = []
    for row_index, row in enumerate(reader, start=2):
        cleaned = {_stringify(key): value for key, value in row.items()}
        rows.append(ParsedImportRow(row_index=row_index, row=cleaned))
    return rows
