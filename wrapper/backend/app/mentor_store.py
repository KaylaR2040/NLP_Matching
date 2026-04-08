from __future__ import annotations

import copy
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

    if field in {"extra_fields"}:
        return value if isinstance(value, dict) else {}

    if value is None:
        return ""
    return str(value).strip()


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
