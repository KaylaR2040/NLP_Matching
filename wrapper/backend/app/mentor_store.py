from __future__ import annotations

import copy
import csv
from io import StringIO
import json
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MENTOR_STORE_PATH = REPO_ROOT / "wrapper" / "backend" / "data" / "mentors" / "mentors_store.json"
DEFAULT_MENTOR_BACKUP_DIR = REPO_ROOT / "wrapper" / "backend" / "data" / "mentors" / "backups"


class MentorStore:
    """File-backed mentor repository.

    NOTE: This is intentionally simple for MVP. In serverless/ephemeral deployments,
    local file writes are not guaranteed durable across instances. Keep all access
    behind this class so it can be replaced by a shared DB/object store later.
    """

    def __init__(
        self,
        *,
        store_path: Path = DEFAULT_MENTOR_STORE_PATH,
        backup_dir: Path = DEFAULT_MENTOR_BACKUP_DIR,
    ) -> None:
        self._store_path = Path(store_path)
        self._backup_dir = Path(backup_dir)
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    @property
    def store_path(self) -> Path:
        return self._store_path

    def load_records(self) -> List[Dict[str, Any]]:
        payload = self._read_payload()
        records = payload.get("records", [])
        if not isinstance(records, list):
            return []
        output: List[Dict[str, Any]] = []
        for row in records:
            if not isinstance(row, dict):
                continue
            normalized = self._normalize_record(row)
            output.append(normalized)
        return output

    def get_by_id(self, mentor_id: str) -> Optional[Dict[str, Any]]:
        target = mentor_id.strip()
        if not target:
            return None
        for record in self.load_records():
            if str(record.get("mentor_id", "")).strip() == target:
                return record
        return None

    def create(self, payload: Dict[str, Any], *, actor: str) -> Dict[str, Any]:
        records = self.load_records()
        base = self._normalize_record(payload)
        if not base.get("mentor_id"):
            base["mentor_id"] = self._generate_mentor_id(base)
        if self.get_by_id(str(base["mentor_id"])) is not None:
            raise ValueError(f"Mentor with id '{base['mentor_id']}' already exists")

        now_iso = _now_iso()
        base["last_modified_at"] = now_iso
        base["last_modified_by"] = actor
        if not base.get("source_timestamp"):
            base["source_timestamp"] = now_iso
        records.append(base)
        self._save_records(records)
        return copy.deepcopy(base)

    def update(self, mentor_id: str, updates: Dict[str, Any], *, actor: str) -> Dict[str, Any]:
        target = mentor_id.strip()
        if not target:
            raise ValueError("mentor_id is required")

        records = self.load_records()
        updated: Optional[Dict[str, Any]] = None
        for index, record in enumerate(records):
            current_id = str(record.get("mentor_id", "")).strip()
            if current_id != target:
                continue

            merged = copy.deepcopy(record)
            for key, value in updates.items():
                if key in IMMUTABLE_FIELDS:
                    continue
                merged[key] = value

            merged = self._normalize_record(merged)
            merged["mentor_id"] = target
            merged["last_modified_at"] = _now_iso()
            merged["last_modified_by"] = actor
            records[index] = merged
            updated = merged
            break

        if updated is None:
            raise KeyError(f"Mentor '{mentor_id}' was not found")

        self._save_records(records)
        return copy.deepcopy(updated)

    def deactivate(self, mentor_id: str, *, actor: str) -> Dict[str, Any]:
        return self.update(mentor_id, {"is_active": False}, actor=actor)

    def import_csv_bytes(
        self,
        content: bytes,
        *,
        source_csv_path: str,
        actor: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        text = content.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(StringIO(text))
        records = self.load_records()

        summary = {
            "rows_read": 0,
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "errors": 0,
            "error_rows": [],
        }

        records_changed = False
        for row_index, row in enumerate(reader, start=2):
            summary["rows_read"] += 1
            try:
                incoming = self._record_from_csv_row(row, source_csv_path=source_csv_path)
                if not self._row_has_identity(incoming):
                    summary["skipped"] += 1
                    continue

                existing_index = self._find_existing_index(records, incoming)
                if existing_index is None:
                    created = self._normalize_record(incoming)
                    if not created.get("mentor_id"):
                        created["mentor_id"] = self._generate_mentor_id(created)
                    now_iso = _now_iso()
                    created["last_modified_at"] = now_iso
                    created["last_modified_by"] = actor
                    if not created.get("source_timestamp"):
                        created["source_timestamp"] = now_iso
                    if not dry_run:
                        records.append(created)
                    summary["created"] += 1
                    records_changed = True
                    continue

                existing = records[existing_index]
                merged = self._merge_incoming(existing, incoming, actor=actor)
                if self._records_equal(existing, merged):
                    summary["unchanged"] += 1
                    continue

                if not dry_run:
                    records[existing_index] = merged
                summary["updated"] += 1
                records_changed = True
            except Exception as exc:  # pragma: no cover - defensive on malformed rows
                summary["errors"] += 1
                summary["error_rows"].append({"row_index": row_index, "error": str(exc)})

        if records_changed and not dry_run:
            self._save_records(records)

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
        filtered.sort(key=lambda row: str(row.get("full_name", "")).strip().lower())

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

        csv_text = output.getvalue()
        return {
            "columns": columns,
            "rows": len(filtered),
            "csv_text": csv_text,
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
        text = export_payload["csv_text"]
        normalized = text.replace("\r\n", "\n")

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
            tmp_file.write(normalized)
            tmp_file.flush()
            temp_path = Path(tmp_file.name)
        temp_path.replace(target)

        return {
            "rows": export_payload["rows"],
            "columns": export_payload["columns"],
            "output_path": str(target),
            "backup_path": str(backup_path) if backup_path else None,
        }

    def _read_payload(self) -> Dict[str, Any]:
        if not self._store_path.exists():
            initial = {
                "schema_version": 1,
                "updated_at": _now_iso(),
                "records": [],
            }
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
        payload = {
            "schema_version": 1,
            "updated_at": _now_iso(),
            "records": records,
        }
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

    def _create_backup_snapshot(self) -> Optional[Path]:
        if not self._store_path.exists():
            return None
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        backup_path = self._backup_dir / f"{timestamp}.json"
        shutil.copy2(self._store_path, backup_path)
        return backup_path

    def _normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        base: Dict[str, Any] = {}
        for key in MENTOR_FIELDS:
            base[key] = _normalize_field(key, record.get(key))

        if not base.get("mentor_id"):
            base["mentor_id"] = self._generate_mentor_id(base)

        base["full_name"] = self._derive_full_name(
            first_name=str(base.get("first_name", "")),
            last_name=str(base.get("last_name", "")),
            fallback=str(base.get("full_name", "")),
            email=str(base.get("email", "")),
        )

        incoming_extra = record.get("extra_fields")
        extra: Dict[str, Any] = {}
        if isinstance(incoming_extra, dict):
            extra.update(incoming_extra)

        for key, value in record.items():
            if key in MENTOR_FIELDS:
                continue
            extra[key] = value
        base["extra_fields"] = extra

        if not str(base.get("source_csv_path", "")).strip():
            base["source_csv_path"] = "nlp_project/data/mentor_real.csv"

        return base

    def _record_from_csv_row(self, row: Dict[str, Any], *, source_csv_path: str) -> Dict[str, Any]:
        normalized = {_normalize_header(key): value for key, value in row.items()}
        extra_fields: Dict[str, Any] = {}
        mapped: Dict[str, Any] = {
            "source_csv_path": source_csv_path or "nlp_project/data/mentor_real.csv",
            "is_active": True,
        }

        for original_key, value in row.items():
            clean_key = (original_key or "").strip()
            if not clean_key:
                continue
            normalized_key = _normalize_header(clean_key)
            mapped_field = CSV_IMPORT_FIELD_BY_HEADER.get(normalized_key)
            if mapped_field:
                mapped[mapped_field] = value
            else:
                extra_fields[clean_key] = value

        timestamp = mapped.get("source_timestamp")
        if not str(timestamp or "").strip():
            timestamp = row.get("Timestamp", "") or row.get("timestamp", "")
        mapped["source_timestamp"] = str(timestamp or "").strip()
        mapped["extra_fields"] = extra_fields

        return self._normalize_record(mapped)

    def _row_has_identity(self, record: Dict[str, Any]) -> bool:
        if str(record.get("email", "")).strip():
            return True
        if str(record.get("linkedin_url", "")).strip():
            return True
        first = str(record.get("first_name", "")).strip()
        last = str(record.get("last_name", "")).strip()
        full = str(record.get("full_name", "")).strip()
        return bool(full or (first and last))

    def _find_existing_index(self, records: List[Dict[str, Any]], incoming: Dict[str, Any]) -> Optional[int]:
        email = str(incoming.get("email", "")).strip().lower()
        linkedin = str(incoming.get("linkedin_url", "")).strip().lower()
        incoming_name = self._normalized_name_key(incoming)

        for index, record in enumerate(records):
            record_email = str(record.get("email", "")).strip().lower()
            if email and record_email and record_email == email:
                return index

        for index, record in enumerate(records):
            record_linkedin = str(record.get("linkedin_url", "")).strip().lower()
            if linkedin and record_linkedin and record_linkedin == linkedin:
                return index

        if incoming_name:
            for index, record in enumerate(records):
                if self._normalized_name_key(record) == incoming_name:
                    return index
        return None

    def _normalized_name_key(self, record: Dict[str, Any]) -> str:
        full_name = str(record.get("full_name", "")).strip()
        if full_name:
            seed = full_name
        else:
            first = str(record.get("first_name", "")).strip()
            last = str(record.get("last_name", "")).strip()
            seed = " ".join(part for part in [first, last] if part)
        normalized = re.sub(r"\\s+", " ", seed).strip().lower()
        return normalized

    def _merge_incoming(self, existing: Dict[str, Any], incoming: Dict[str, Any], *, actor: str) -> Dict[str, Any]:
        merged = copy.deepcopy(existing)
        for key in MENTOR_FIELDS:
            if key in {"mentor_id", "last_modified_at", "last_modified_by", "extra_fields"}:
                continue
            value = incoming.get(key)
            if _is_non_empty_value(value):
                merged[key] = value

        merged_extra: Dict[str, Any] = {}
        if isinstance(existing.get("extra_fields"), dict):
            merged_extra.update(existing["extra_fields"])
        if isinstance(incoming.get("extra_fields"), dict):
            for key, value in incoming["extra_fields"].items():
                if _is_non_empty_value(value):
                    merged_extra[key] = value
        merged["extra_fields"] = merged_extra
        merged["last_modified_at"] = _now_iso()
        merged["last_modified_by"] = actor

        return self._normalize_record(merged)

    def _records_equal(self, left: Dict[str, Any], right: Dict[str, Any]) -> bool:
        ignore = {"last_modified_at", "last_modified_by"}
        left_norm = {k: v for k, v in self._normalize_record(left).items() if k not in ignore}
        right_norm = {k: v for k, v in self._normalize_record(right).items() if k not in ignore}
        return left_norm == right_norm

    def _csv_row_from_record(self, record: Dict[str, Any], *, extra_columns: List[str]) -> Dict[str, Any]:
        extras = record.get("extra_fields")
        if not isinstance(extras, dict):
            extras = {}

        city = str(record.get("current_city", "")).strip()
        state = str(record.get("current_state", "")).strip()
        location = str(record.get("current_location", "")).strip()
        if not location:
            location = ", ".join(part for part in [city, state] if part)

        row = {
            "Timestamp": str(record.get("source_timestamp", "")).strip(),
            "Email": str(record.get("email", "")).strip(),
            "LinkedIn": str(record.get("linkedin_url", "")).strip(),
            "First Name": str(record.get("first_name", "")).strip(),
            "Last Name": str(record.get("last_name", "")).strip(),
            "Pronouns": _extra_value(extras, ["Pronouns", "pronouns"]),
            "Degrees": str(record.get("degrees_text", "")).strip(),
            "Current City": city,
            "Current State": state,
            "Current City State": location,
            "Current Job Title": str(record.get("current_job_title", "")).strip(),
            "Current Company": str(record.get("current_company", "")).strip(),
            "Previous Mentorship": _extra_value(extras, ["Previous Mentorship", "previous mentorship"]),
            "Industry Focus Area": str(record.get("industry_focus_area", "")).strip(),
            "Previous Involvement": _extra_value(extras, ["Previous Involvement", "previous involvement"]),
            "Previous Involvement Organizations": _extra_value(
                extras,
                [
                    "Previous Involvement Organizations",
                    "previous involvement organizations",
                ],
            ),
            "Why Interested": _extra_value(extras, ["Why Interested", "why interested"]),
            "Professional Experience": str(record.get("professional_experience", "")).strip(),
            "About Yourself": str(record.get("about_yourself", "")).strip(),
            "Students Interested": str(record.get("students_interested", 0)).strip(),
            "Profile Photo URL": str(record.get("profile_photo_url", "")).strip(),
            "Phone": str(record.get("phone", "")).strip(),
            "Preferred Contact Method": str(record.get("preferred_contact_method", "")).strip(),
            "Is Active": "true" if bool(record.get("is_active", True)) else "false",
            "Mentor ID": str(record.get("mentor_id", "")).strip(),
            "Last Modified At": str(record.get("last_modified_at", "")).strip(),
            "Last Modified By": str(record.get("last_modified_by", "")).strip(),
            "Last Enriched At": str(record.get("last_enriched_at", "")).strip(),
            "Enrichment Status": str(record.get("enrichment_status", "")).strip(),
        }
        for key in extra_columns:
            if key not in row:
                row[key] = _stringify(extras.get(key, ""))
        return row

    def _generate_mentor_id(self, record: Dict[str, Any]) -> str:
        email = str(record.get("email", "")).strip().lower()
        if email:
            return email

        first = str(record.get("first_name", "")).strip().lower()
        last = str(record.get("last_name", "")).strip().lower()
        linked_in = str(record.get("linkedin_url", "")).strip().lower()

        seed = "-".join(part for part in [first, last, linked_in] if part)
        if not seed:
            seed = f"mentor-{int(time.time() * 1000)}"
        slug = re.sub(r"[^a-z0-9]+", "-", seed).strip("-")
        return slug or f"mentor-{int(time.time() * 1000)}"

    def _derive_full_name(self, *, first_name: str, last_name: str, fallback: str, email: str) -> str:
        name = " ".join(part for part in [first_name.strip(), last_name.strip()] if part).strip()
        if name:
            return name
        if fallback.strip():
            return fallback.strip()
        if email.strip():
            return email.strip()
        return "Unknown Mentor"


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


def _normalize_field(field: str, value: Any) -> Any:
    if field in {"students_interested"}:
        if value is None:
            return 0
        text = str(value).strip()
        if not text:
            return 0
        match = re.search(r"(\d+)", text)
        if not match:
            return 0
        return int(match.group(1))

    if field in {"is_active"}:
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"", "none", "null"}:
            return True
        return text in {"1", "true", "yes", "y", "active"}

    if field in {"extra_fields", "enrichment_provider_metadata"}:
        return value if isinstance(value, dict) else {}

    if value is None:
        return ""
    return str(value).strip()


def _normalize_header(value: str) -> str:
    lowered = (value or "").strip().lower()
    lowered = re.sub(r"\\s+", " ", lowered)
    return lowered


def _is_non_empty_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, dict):
        return len(value) > 0
    if isinstance(value, bool):
        return True
    if isinstance(value, int):
        return value != 0
    text = str(value).strip()
    return text != ""


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


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


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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
