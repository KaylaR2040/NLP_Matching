from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests


# Update these links whenever the underlying Google Form entry IDs change.
MENTOR_PREFILLED_LINK = (
    "https://docs.google.com/forms/d/e/1FAIpQLSey0OLTdTUXmcLp8LLo9UxCuVMrvoXeSm9jDNW9TcMwx5ex6w/"
    "viewform?usp=pp_url&entry.1212118616=Keradu@ncsu&entry.1405593720=j&entry.1460354148=j&"
    "entry.1280480792=j&entry.850687584=j&entry.1549300576=j&entry.1535534221=n&entry.169312866=nj"
    "&entry.2127194621=j&entry.1560582362=j&entry.112498215=adfjkla&entry.1972480795=dlfkajksdf&"
    "entry.1890802982=adfasdf&entry.1378992134=adfadsfa&entry.1154429959=asdfadsf&entry.76845075="
    "adfsadf&entry.1753687772=asdfasdfa&entry.1326101346=adfasdfasdf&entry.687618411=asdfasdfa&"
    "entry.807591165=%7B%22%22%7D"
)

MENTOR_FIELD_ORDER: List[str] = [
    "email",
    "linkedin",
    "firstName",
    "lastName",
    "pronouns",
    "degreesSummary",
    "currentCity",
    "currentState",
    "currentCityState",
    "currentJobTitle",
    "currentCompany",
    "previousMentorship",
    "industryFocusArea",
    "previousInvolvement",
    "previousInvolvementOrgs",
    "whyInterested",
    "professionalExperience",
    "aboutYourself",
    "studentsInterested",
]

MENTEE_PREFILLED_LINK = (
    "https://docs.google.com/forms/d/e/1FAIpQLScEp0vvZtkpEtWFxPthh5xbGr0rcEt5k6Zd8CjbTeXHT-VskA/"
    "viewform?usp=pp_url&entry.949801267=h&entry.926900860=h&entry.1983684609=h&entry.1976491083=h"
    "&entry.1337254110=h&entry.1583993810=h&entry.1943297115=h&entry.2094001975=h&entry.1479506346="
    "h&entry.1579760704=k%0A&entry.2117423693=k&entry.705448099=k&entry.562009089=k&entry.2016076981="
    "k&entry.867933932=k&entry.1834469658=k&entry.162617210=k&entry.549463769=k&entry.1801459898=k"
    "&entry.76037252=k&entry.1948682182=k&entry.1538022217=k&entry.1192108296=k&entry.1799865324=k"
    "&entry.2061509335=j"
)

MENTEE_FIELD_ORDER: List[str] = [
    "email",
    "firstName",
    "lastName",
    "pronouns",
    "educationLevel",
    "graduationSemester",
    "graduationYear",
    "degreePrograms",
    "hasConcentration",
    "concentrations",
    "phdSpecialization",
    "previousMentorship",
    "studentOrgs",
    "experienceLevel",
    "industriesOfInterest",
    "aboutYourself",
    "matchByIndustry",
    "matchByDegree",
    "matchByClubs",
    "matchByIdentity",
    "matchByGradYears",
    "helpTopics",
    "submissionId",
    "submittedAt",
]


@dataclass
class GoogleFormConfig:
    form_name: str
    enabled: bool
    required: bool
    response_url: str
    field_map: Dict[str, str]


def _parse_bool(value: Any, default_value: bool) -> bool:
    if value in (None, ""):
        return default_value
    return str(value).strip().lower() == "true"


def _parse_json_object(raw: str, default_value: Dict[str, str]) -> Dict[str, str]:
    if not raw:
        return default_value
    try:
        parsed = json.loads(raw)
    except Exception:
        return default_value
    if not isinstance(parsed, dict):
        return default_value
    normalized: Dict[str, str] = {}
    for key, value in parsed.items():
        if key is None or value is None:
            continue
        normalized[str(key)] = str(value)
    return normalized or default_value


def normalize_google_form_response_url(raw_url: str) -> str:
    if not raw_url:
        return ""

    cleaned = str(raw_url).strip().replace("|", "I")
    if not cleaned:
        return ""

    try:
        parsed = urlparse(cleaned)
    except Exception:
        return cleaned

    if not parsed.scheme or not parsed.netloc:
        return cleaned

    new_path = parsed.path
    if new_path.endswith("/viewform"):
        new_path = f"{new_path[:-len('/viewform')]}/formResponse"

    return urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, "", parsed.fragment))


def build_field_map_from_prefilled_link(prefilled_link: str, field_order: Iterable[str]) -> Dict[str, str]:
    field_names = [str(item) for item in field_order]
    if not field_names:
        raise ValueError("field_order must be a non-empty sequence")

    parsed = urlparse(prefilled_link)
    entry_ids = [
        key
        for key, _value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.startswith("entry.")
    ]

    if len(entry_ids) < len(field_names):
        raise ValueError(
            f"Prefilled link has {len(entry_ids)} entry ids but at least {len(field_names)} are required"
        )

    return {field_names[idx]: entry_ids[idx] for idx in range(len(field_names))}


def build_google_form_config(
    *,
    form_name: str,
    env_prefix: str,
    prefilled_link: str,
    field_order: Iterable[str],
    default_enabled: bool = True,
    default_required: bool = True,
) -> GoogleFormConfig:
    if not prefilled_link:
        raise ValueError(f"Missing prefilled link for {form_name} form config")

    default_response_url = normalize_google_form_response_url(prefilled_link)
    default_field_map = build_field_map_from_prefilled_link(prefilled_link, field_order)

    enabled = _parse_bool(os.getenv(f"{env_prefix}_ENABLED"), default_enabled)
    required = _parse_bool(os.getenv(f"{env_prefix}_REQUIRED"), default_required)
    response_url = os.getenv(f"{env_prefix}_RESPONSE_URL", "").strip() or default_response_url
    response_url = normalize_google_form_response_url(response_url)
    field_map = _parse_json_object(os.getenv(f"{env_prefix}_FIELD_MAP_JSON", ""), default_field_map)

    return GoogleFormConfig(
        form_name=form_name,
        enabled=enabled,
        required=required,
        response_url=response_url,
        field_map=field_map,
    )


def _resolve_path(data: Dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in str(dotted_path).split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return ", ".join(_stringify_value(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _build_payload(config: GoogleFormConfig, submission_data: Dict[str, Any]) -> List[Tuple[str, str]]:
    payload: List[Tuple[str, str]] = []
    for source_path, entry_id in config.field_map.items():
        resolved = _resolve_path(submission_data, source_path)
        if resolved is None:
            continue
        if isinstance(resolved, list):
            payload.extend((entry_id, _stringify_value(item)) for item in resolved)
        else:
            payload.append((entry_id, _stringify_value(resolved)))

    if not payload:
        raise ValueError("Google Form entry configuration is missing")

    return payload


def _find_empty_required_entries(
    field_map: Dict[str, str], payload: List[Tuple[str, str]]
) -> List[str]:
    missing: List[str] = []
    for entry_id in field_map.values():
        values = [value for key, value in payload if key == entry_id]
        if not values or all(not str(item).strip() for item in values):
            missing.append(entry_id)
    return missing


def _describe_google_form_http_error(status_code: int) -> str:
    if status_code == 401:
        return (
            "Google Form returned HTTP 401. This form currently requires Google sign-in "
            "or organization access. Disable form sign-in restriction, or submit through "
            "a logged-in browser session for the same Google Workspace domain."
        )
    return f"Google Form returned HTTP {status_code}"


def submit_to_google_form(
    config: GoogleFormConfig,
    submission_data: Dict[str, Any],
    timeout_seconds: float,
) -> Dict[str, Any]:
    if not config.enabled or not config.response_url:
        return {
            "forwarded": False,
            "skipped": True,
            "status_code": None,
            "reason": f"{config.form_name} Google Form forwarding is disabled or unconfigured",
        }

    payload = _build_payload(config, submission_data)
    encoded_payload = urlencode(payload, doseq=True)

    try:
        response = requests.post(
            config.response_url,
            data=encoded_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=timeout_seconds,
        )
        ok = response.status_code < 400
        if not ok and config.required:
            response_text = response.text[:500]
            missing_entries = _find_empty_required_entries(config.field_map, payload)
            missing_info = (
                f" Empty mapped entries: {', '.join(missing_entries)}."
                if missing_entries
                else ""
            )
            raise RuntimeError(
                f"{_describe_google_form_http_error(response.status_code)}.{missing_info} "
                f"Response snippet: {response_text}"
            )

        return {
            "forwarded": ok,
            "skipped": not ok,
            "status_code": response.status_code,
            "reason": (
                "Submitted to Google Form"
                if ok
                else _describe_google_form_http_error(response.status_code)
            ),
        }
    except Exception as exc:
        if config.required:
            raise
        return {
            "forwarded": False,
            "skipped": True,
            "status_code": None,
            "reason": f"Google Form request failed: {exc}",
        }
