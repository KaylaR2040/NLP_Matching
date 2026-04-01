from datetime import datetime
from typing import Dict, List


def _normalize_email(value):
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def _parse_submission_timestamp(record: Dict, fallback_index: int) -> tuple[int, datetime, int]:
    raw_value = record.get("submitted_at") or record.get("submittedAt")
    if isinstance(raw_value, str) and raw_value.strip():
        normalized = raw_value.strip().replace("Z", "+00:00")
        try:
            return (0, datetime.fromisoformat(normalized), fallback_index)
        except ValueError:
            pass
    return (1, datetime.min, fallback_index)


def dedupe_mentees_by_email(mentee_records: List[Dict]) -> tuple[List[Dict], int, int]:
    grouped_records: Dict[str, List[tuple[int, Dict]]] = {}
    deduped_records_with_index: List[tuple[int, Dict]] = []
    skipped_count = 0

    for index, record in enumerate(mentee_records):
        email = _normalize_email(record.get("email"))
        if not email:
            deduped_records_with_index.append((index, record))
            continue
        grouped_records.setdefault(email, []).append((index, record))

    duplicate_emails = 0
    for entries in grouped_records.values():
        if len(entries) == 1:
            deduped_records_with_index.append(entries[0])
            continue

        duplicate_emails += 1
        entries.sort(key=lambda item: _parse_submission_timestamp(item[1], item[0]))
        deduped_records_with_index.append(entries[0])
        skipped_count += len(entries) - 1

    deduped_records_with_index.sort(key=lambda item: item[0])
    return [record for _, record in deduped_records_with_index], duplicate_emails, skipped_count


def _is_not_participating_this_semester(value) -> bool:
    if isinstance(value, bool):
        return value is False
    if isinstance(value, str):
        return value.strip().lower() in {"false", "no", "n", "0"}
    return False


def filter_opted_out_mentors(mentor_records: List[Dict]) -> tuple[List[Dict], int]:
    kept_records: List[Dict] = []
    removed_count = 0

    for record in mentor_records:
        if _is_not_participating_this_semester(record.get("participatingThisSemester", True)):
            removed_count += 1
            continue
        kept_records.append(record)

    return kept_records, removed_count
