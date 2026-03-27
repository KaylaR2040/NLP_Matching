import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional
from urllib import error, parse, request

_DEFAULT_MENTEE_FIELD_MAP = {
    "email": "entry.949801267",
    "firstName": "entry.926900860",
    "lastName": "entry.1983684609",
    "pronouns": "entry.1976491083",
    "educationLevel": "entry.1337254110",
    "graduationSemester": "entry.1583993810",
    "graduationYear": "entry.1943297115",
    "degreePrograms": "entry.2094001975",
    "hasConcentration": "entry.1479506346",
    "concentrations": "entry.1579760704",
    "phdSpecialization": "entry.2117423693",
    "previousMentorship": "entry.705448099",
    "studentOrgs": "entry.562009089",
    "experienceLevel": "entry.2016076981",
    "industriesOfInterest": "entry.867933932",
    "aboutYourself": "entry.1834469658",
    "matchByIndustry": "entry.162617210",
    "matchByDegree": "entry.549463769",
    "matchByClubs": "entry.1801459898",
    "matchByIdentity": "entry.76037252",
    "matchByGradYears": "entry.1948682182",
    "helpTopics": "entry.1538022217",
    "submissionId": "entry.1192108296",
    "submittedAt": "entry.1799865324",
}


class GoogleFormSubmissionError(RuntimeError):
    """Raised when a Google Form submission cannot be completed."""


@dataclass(frozen=True)
class GoogleFormConfig:
    form_name: str
    response_url: str = ""
    json_entry_id: str = ""
    field_map: Mapping[str, str] = field(default_factory=dict)
    enabled: bool = False
    required: bool = False

    def is_configured(self) -> bool:
        if not self.enabled or not self.response_url:
            return False
        return bool(self.json_entry_id or self.field_map)


@dataclass(frozen=True)
class GoogleFormResult:
    forwarded: bool
    skipped: bool
    status_code: Optional[int] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "forwarded": self.forwarded,
            "skipped": self.skipped,
            "status_code": self.status_code,
            "reason": self.reason,
        }


def get_google_form_config(form_type: str) -> GoogleFormConfig:
    normalized = form_type.strip().lower()

    if normalized == "mentee":
        default_url = (
            "https://docs.google.com/forms/d/e/"
            "1FAIpQLScEp0vvZtkpEtWFxPthh5xbGr0rcEt5k6Zd8CjbTeXHT-VskA/"
            "formResponse"
        )
        return GoogleFormConfig(
            form_name="mentee",
            response_url=_normalize_google_form_response_url(
                os.getenv("MENTEE_GOOGLE_FORM_RESPONSE_URL", default_url)
            ),
            json_entry_id=os.getenv("MENTEE_GOOGLE_FORM_JSON_ENTRY_ID", ""),
            field_map=_parse_field_map(
                os.getenv("MENTEE_GOOGLE_FORM_FIELD_MAP_JSON"),
                _DEFAULT_MENTEE_FIELD_MAP,
            ),
            enabled=os.getenv("MENTEE_GOOGLE_FORM_ENABLED", "true").lower()
            == "true",
            required=os.getenv("MENTEE_GOOGLE_FORM_REQUIRED", "true").lower()
            == "true",
        )

    if normalized == "mentor":
        default_mentor_url = (
            "https://docs.google.com/forms/d/e/"
            "1FAIpQLSes-SnnWAMcXzU_CsX6opYIpKxGu3Ii1BqfhMDUfN9IV4-pqQ/"
            "formResponse"
        )
        return GoogleFormConfig(
            form_name="mentor",
            response_url=_normalize_google_form_response_url(
                os.getenv("MENTOR_GOOGLE_FORM_RESPONSE_URL", default_mentor_url)
            ),
            json_entry_id=os.getenv("MENTOR_GOOGLE_FORM_JSON_ENTRY_ID", "entry.1048570048"),
            field_map=_parse_field_map(
                os.getenv("MENTOR_GOOGLE_FORM_FIELD_MAP_JSON"),
                {},
            ),
            enabled=os.getenv("MENTOR_GOOGLE_FORM_ENABLED", "true").lower()
            == "true",
            required=os.getenv("MENTOR_GOOGLE_FORM_REQUIRED", "true").lower()
            == "true",
        )

    raise ValueError(f"Unsupported form type: {form_type}")


def submit_google_form(form_type: str, submission_data: Dict[str, Any]) -> GoogleFormResult:
    config = get_google_form_config(form_type)

    if not config.is_configured():
        return GoogleFormResult(
            forwarded=False,
            skipped=True,
            reason=f"{config.form_name} Google Form forwarding is disabled or incomplete",
        )

    encoded_payload = parse.urlencode(_build_payload(config, submission_data)).encode(
        "utf-8"
    )
    http_request = request.Request(
        config.response_url,
        data=encoded_payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "ncsu-mentorship-backend/1.0",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=10) as response:
            return GoogleFormResult(
                forwarded=True,
                skipped=False,
                status_code=response.getcode(),
                reason="Submitted to Google Form",
            )
    except error.HTTPError as exc:
        if not config.required:
            return GoogleFormResult(
                forwarded=False,
                skipped=True,
                status_code=exc.code,
                reason=_describe_google_form_http_error(exc.code),
            )
        raise GoogleFormSubmissionError(
            _describe_google_form_http_error(exc.code)
        ) from exc
    except error.URLError as exc:
        if not config.required:
            return GoogleFormResult(
                forwarded=False,
                skipped=True,
                reason=f"Google Form request failed: {exc.reason}",
            )
        raise GoogleFormSubmissionError(
            f"Google Form request failed: {exc.reason}"
        ) from exc


def _build_payload(
    config: GoogleFormConfig,
    submission_data: Dict[str, Any],
) -> Dict[str, str]:
    if config.field_map:
        payload: Dict[str, str] = {}
        for source_path, entry_id in config.field_map.items():
            resolved_value = _resolve_path(submission_data, source_path)
            if resolved_value is None:
                continue
            payload[entry_id] = _stringify_value(resolved_value)
        if payload:
            return payload

    if config.json_entry_id:
        return {
            config.json_entry_id: json.dumps(
                submission_data,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            ),
        }

    raise GoogleFormSubmissionError(
        f"{config.form_name} Google Form config is missing entry mappings"
    )


def _resolve_path(data: Dict[str, Any], source_path: str) -> Any:
    current: Any = data
    for segment in source_path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "YES" if value else "NO"
    if isinstance(value, list):
        return ", ".join(_stringify_value(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


def _parse_field_map(raw_json: Optional[str], default: Mapping[str, str]) -> Mapping[str, str]:
    if not raw_json:
        return dict(default)

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        return dict(default)

    if not isinstance(parsed, dict):
        return dict(default)

    normalized: Dict[str, str] = {}
    for key, value in parsed.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        normalized[key] = value

    return normalized or dict(default)


def _normalize_google_form_response_url(raw_url: str) -> str:
    cleaned = raw_url.strip().replace("|", "I")
    if not cleaned:
        return ""

    parsed = parse.urlparse(cleaned)
    if parsed.path.endswith("/viewform"):
        path = parsed.path[: -len("/viewform")] + "/formResponse"
        parsed = parsed._replace(path=path, query="")
        return parse.urlunparse(parsed)

    return cleaned


def _describe_google_form_http_error(status_code: int) -> str:
    if status_code == 401:
        return (
            "Google Form returned HTTP 401. This form currently requires Google "
            "sign-in or organization access. Disable form sign-in restriction, "
            "or submit through a logged-in browser session for the same domain."
        )
    return f"Google Form returned HTTP {status_code}"
