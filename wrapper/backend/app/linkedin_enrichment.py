from __future__ import annotations

import logging
import os
import re
import time
from html import unescape
from urllib.parse import quote
from urllib.parse import parse_qs, unquote, urlparse, urlunparse
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol

import requests


LOG = logging.getLogger("wrapper.linkedin")


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _first_non_empty(payload: Dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = payload.get(key)
        text = _clean(value)
        if text:
            return text
    return ""


def _strip_tags(value: str) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_linkedin_slug(linkedin_url: str) -> str:
    try:
        parsed = urlparse(linkedin_url)
    except Exception:
        return ""
    path_parts = [part for part in parsed.path.split("/") if part.strip()]
    if len(path_parts) >= 2 and path_parts[0].lower() in {"in", "pub"}:
        return path_parts[1].strip()
    return ""


def normalize_linkedin_profile_url(linkedin_url: str) -> tuple[str, str]:
    raw = _clean(linkedin_url)
    if not raw:
        return "", "LinkedIn URL is empty."

    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"

    try:
        parsed = urlparse(raw)
    except Exception:
        return "", "LinkedIn URL is invalid."

    host = parsed.netloc.strip().lower()
    if host.startswith("m."):
        host = host[2:]
    if host.startswith("www."):
        host = host[4:]
    if not host.endswith("linkedin.com"):
        return "", "LinkedIn URL must use linkedin.com."

    path_parts = [part for part in parsed.path.split("/") if part.strip()]
    if len(path_parts) < 2 or path_parts[0].lower() not in {"in", "pub"}:
        return "", "LinkedIn URL must look like linkedin.com/in/<profile-slug>."
    slug = path_parts[1].strip()
    if not slug:
        return "", "LinkedIn profile slug is missing."

    normalized_path = f"/in/{slug}"
    normalized = urlunparse(("https", "www.linkedin.com", normalized_path, "", "", ""))
    return normalized, ""


def _extract_redirect_target(url: str) -> str:
    value = _clean(url)
    if not value:
        return ""
    if value.startswith("//"):
        value = f"https:{value}"
    try:
        parsed = urlparse(value)
    except Exception:
        return value
    if "duckduckgo.com" not in parsed.netloc:
        return value
    query = parse_qs(parsed.query)
    target = query.get("uddg", [])
    if not target:
        return value
    return unquote(target[0])


def _resolve_public_profile_photo_url(
    linkedin_url: str,
    *,
    timeout_seconds: float,
) -> tuple[str, Dict[str, Any]]:
    slug = _extract_linkedin_slug(linkedin_url)
    if not slug:
        return "", {"attempted": False, "reason": "missing_slug"}

    template = os.getenv(
        "WRAPPER_LINKEDIN_PUBLIC_PHOTO_ENDPOINT_TEMPLATE",
        "https://unavatar.io/linkedin/{slug}?fallback=false",
    ).strip()
    endpoint = template.replace("{slug}", quote(slug, safe=""))
    metadata: Dict[str, Any] = {
        "attempted": True,
        "provider": "unavatar",
        "endpoint": endpoint,
    }
    try:
        response = requests.get(
            endpoint,
            timeout=timeout_seconds,
            allow_redirects=True,
        )
    except Exception as exc:
        metadata["error"] = str(exc)
        return "", metadata

    metadata["http_status"] = response.status_code
    content_type = _clean(response.headers.get("content-type")).lower()
    metadata["content_type"] = content_type
    if response.status_code >= 400:
        return "", metadata
    if not content_type.startswith("image/"):
        return "", metadata
    return endpoint, metadata


@dataclass
class LinkedInEnrichmentResult:
    status: str
    message: str
    updates: Dict[str, Any] = field(default_factory=dict)
    provider_metadata: Dict[str, Any] = field(default_factory=dict)


class LinkedInEnrichmentProvider(Protocol):
    name: str

    def enrich(self, linkedin_url: str) -> LinkedInEnrichmentResult:
        ...


class DisabledLinkedInEnrichmentProvider:
    name = "disabled"

    def __init__(self, reason: str) -> None:
        self._reason = reason

    @property
    def reason(self) -> str:
        return self._reason

    def enrich(self, linkedin_url: str) -> LinkedInEnrichmentResult:
        _ = linkedin_url
        return LinkedInEnrichmentResult(
            status="disabled",
            message=self._reason,
            updates={},
            provider_metadata={},
        )


class MockLinkedInEnrichmentProvider:
    name = "mock"

    def enrich(self, linkedin_url: str) -> LinkedInEnrichmentResult:
        slug = _clean(linkedin_url).rstrip("/").split("/")[-1]
        if not slug:
            slug = "mentor"
        safe_slug = quote(slug, safe="")
        city = os.getenv("WRAPPER_LINKEDIN_MOCK_CITY", "Raleigh")
        state = os.getenv("WRAPPER_LINKEDIN_MOCK_STATE", "NC")
        updates = {
            "profile_photo_url": (
                "https://ui-avatars.com/api/"
                f"?name={safe_slug}&background=CC0000&color=fff&size=256"
            ),
            "current_company": os.getenv(
                "WRAPPER_LINKEDIN_MOCK_COMPANY",
                "NCSU ECE Mentor Network",
            ),
            "current_job_title": os.getenv(
                "WRAPPER_LINKEDIN_MOCK_TITLE",
                "Mentor",
            ),
            "current_city": city,
            "current_state": state,
            "current_location": f"{city}, {state}",
        }
        return LinkedInEnrichmentResult(
            status="success",
            message="Mock enrichment completed.",
            updates=updates,
            provider_metadata={"provider": self.name, "mock": True},
        )


class ProxycurlLinkedInEnrichmentProvider:
    name = "proxycurl"

    def __init__(self, *, api_key: str, timeout_seconds: float = 20.0) -> None:
        self._api_key = api_key.strip()
        self._timeout_seconds = timeout_seconds
        self._endpoint = os.getenv(
            "WRAPPER_LINKEDIN_PROXYCURL_ENDPOINT",
            "https://nubela.co/proxycurl/api/v2/linkedin",
        ).strip()

    def enrich(self, linkedin_url: str) -> LinkedInEnrichmentResult:
        if not self._api_key:
            return LinkedInEnrichmentResult(
                status="disabled",
                message="Proxycurl API key is not configured.",
            )

        headers = {"Authorization": f"Bearer {self._api_key}"}
        params = {
            "url": linkedin_url,
            "fallback_to_cache": "on-error",
            "use_cache": "if-present",
        }

        try:
            response = requests.get(
                self._endpoint,
                params=params,
                headers=headers,
                timeout=self._timeout_seconds,
            )
        except Exception as exc:
            return LinkedInEnrichmentResult(
                status="failed",
                message=f"Provider request failed: {exc}",
                provider_metadata={"provider": self.name},
            )
        LOG.info(
            "linkedin_provider_request provider=%s endpoint=%s status=%s linkedin_url=%s",
            self.name,
            self._endpoint,
            response.status_code,
            linkedin_url,
        )

        metadata = {
            "provider": self.name,
            "http_status": response.status_code,
            "endpoint": self._endpoint,
        }
        if response.status_code >= 400:
            return LinkedInEnrichmentResult(
                status="failed",
                message=f"Provider returned HTTP {response.status_code}.",
                provider_metadata=metadata,
            )

        payload: Dict[str, Any]
        try:
            decoded = response.json()
        except ValueError:
            decoded = {}
        payload = decoded if isinstance(decoded, dict) else {}

        updates = _extract_updates(payload)
        metadata["raw"] = payload
        metadata["extracted_fields"] = sorted(updates.keys())
        if not updates:
            return LinkedInEnrichmentResult(
                status="failed",
                message="Provider returned no usable profile fields.",
                provider_metadata=metadata,
            )

        return LinkedInEnrichmentResult(
            status="success",
            message="LinkedIn enrichment completed.",
            updates=updates,
            provider_metadata=metadata,
        )


class HttpLinkedInEnrichmentProvider:
    name = "http"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._base_url = base_url.strip()
        self._api_key = api_key.strip()
        self._timeout_seconds = timeout_seconds
        self._api_key_header = os.getenv(
            "WRAPPER_LINKEDIN_PROVIDER_API_KEY_HEADER",
            "Authorization",
        ).strip()
        self._api_key_prefix = os.getenv(
            "WRAPPER_LINKEDIN_PROVIDER_API_KEY_PREFIX",
            "Bearer ",
        )
        self._url_param_name = os.getenv(
            "WRAPPER_LINKEDIN_PROVIDER_URL_PARAM",
            "linkedin_url",
        ).strip()

    def enrich(self, linkedin_url: str) -> LinkedInEnrichmentResult:
        if not self._base_url:
            return LinkedInEnrichmentResult(
                status="disabled",
                message="HTTP provider URL is not configured.",
            )

        headers: Dict[str, str] = {}
        if self._api_key:
            headers[self._api_key_header] = f"{self._api_key_prefix}{self._api_key}"

        params = {self._url_param_name: linkedin_url}
        try:
            response = requests.get(
                self._base_url,
                params=params,
                headers=headers,
                timeout=self._timeout_seconds,
            )
        except Exception as exc:
            return LinkedInEnrichmentResult(
                status="failed",
                message=f"Provider request failed: {exc}",
                provider_metadata={"provider": self.name},
            )
        LOG.info(
            "linkedin_provider_request provider=%s endpoint=%s status=%s linkedin_url=%s",
            self.name,
            self._base_url,
            response.status_code,
            linkedin_url,
        )

        metadata = {
            "provider": self.name,
            "http_status": response.status_code,
            "endpoint": self._base_url,
        }
        if response.status_code >= 400:
            return LinkedInEnrichmentResult(
                status="failed",
                message=f"Provider returned HTTP {response.status_code}.",
                provider_metadata=metadata,
            )

        try:
            decoded = response.json()
        except ValueError:
            decoded = {}
        payload = decoded if isinstance(decoded, dict) else {}
        updates = _extract_updates(payload)
        metadata["raw"] = payload
        metadata["extracted_fields"] = sorted(updates.keys())

        if not updates:
            return LinkedInEnrichmentResult(
                status="failed",
                message="Provider returned no usable profile fields.",
                provider_metadata=metadata,
            )

        return LinkedInEnrichmentResult(
            status="success",
            message="LinkedIn enrichment completed.",
            updates=updates,
            provider_metadata=metadata,
        )


class DuckDuckGoLinkedInEnrichmentProvider:
    name = "duckduckgo"

    def __init__(self, *, timeout_seconds: float = 20.0) -> None:
        self._timeout_seconds = timeout_seconds
        self._endpoint = os.getenv(
            "WRAPPER_LINKEDIN_SEARCH_ENDPOINT",
            "https://duckduckgo.com/html/",
        ).strip()
        self._user_agent = os.getenv(
            "WRAPPER_LINKEDIN_SEARCH_USER_AGENT",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        ).strip()

    def enrich(self, linkedin_url: str) -> LinkedInEnrichmentResult:
        slug = _extract_linkedin_slug(linkedin_url)
        if not slug:
            return LinkedInEnrichmentResult(
                status="failed",
                message="Unable to derive LinkedIn profile slug from URL.",
                provider_metadata={"provider": self.name},
            )

        query = f'site:linkedin.com/in "{slug}"'
        headers = {
            "User-Agent": self._user_agent,
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            response = requests.get(
                self._endpoint,
                params={"q": query},
                headers=headers,
                timeout=self._timeout_seconds,
            )
        except Exception as exc:
            return LinkedInEnrichmentResult(
                status="failed",
                message=f"Search provider request failed: {exc}",
                provider_metadata={"provider": self.name, "query": query},
            )

        metadata: Dict[str, Any] = {
            "provider": self.name,
            "http_status": response.status_code,
            "endpoint": self._endpoint,
            "query": query,
        }
        LOG.info(
            "linkedin_provider_request provider=%s endpoint=%s query=%s status=%s",
            self.name,
            self._endpoint,
            query,
            response.status_code,
        )
        if response.status_code >= 400:
            return LinkedInEnrichmentResult(
                status="failed",
                message=f"Search provider returned HTTP {response.status_code}.",
                provider_metadata=metadata,
            )

        html_text = response.text
        title_matches = re.findall(
            r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            html_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        snippet_matches = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</(?:a|div)>',
            html_text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if not title_matches:
            return LinkedInEnrichmentResult(
                status="failed",
                message="Search provider returned no LinkedIn profile matches.",
                provider_metadata=metadata,
            )

        top_href, top_title_raw = title_matches[0]
        top_result_url = _extract_redirect_target(top_href)
        if "linkedin.com/in/" not in top_result_url.lower():
            return LinkedInEnrichmentResult(
                status="failed",
                message="Search provider did not return a LinkedIn profile result.",
                provider_metadata=metadata,
            )
        top_title = _strip_tags(top_title_raw)
        top_snippet = _strip_tags(snippet_matches[0] if snippet_matches else "")
        metadata["top_result_url"] = top_result_url
        metadata["top_result_title"] = top_title
        metadata["top_result_snippet"] = top_snippet

        updates: Dict[str, Any] = {}
        headline = top_title
        if "|" in headline:
            headline = headline.split("|", 1)[0].strip()
        if " - " in headline:
            _, maybe_headline = headline.split(" - ", 1)
            headline = maybe_headline.strip()

        candidate_texts = [headline, top_snippet]
        company = ""
        title = ""
        for text in candidate_texts:
            match = re.search(
                r"(?P<title>.+?)\s+at\s+(?P<company>[A-Za-z0-9&,. \-]{2,})",
                text,
                flags=re.IGNORECASE,
            )
            if match:
                maybe_title = _clean(match.group("title"))
                maybe_company = _clean(match.group("company"))
                if maybe_title and not title:
                    title = maybe_title
                if maybe_company and not company:
                    company = maybe_company
                if title and company:
                    break

        if company:
            updates["current_company"] = company
        if title:
            updates["current_job_title"] = title

        location_match = re.search(
            r"(?:Location:|location:)\s*([A-Za-z0-9,.\- ]{2,})",
            top_snippet,
            flags=re.IGNORECASE,
        )
        if location_match:
            location = _clean(location_match.group(1))
            if location:
                updates["current_location"] = location
                city_state = [part.strip() for part in location.split(",") if part.strip()]
                if len(city_state) >= 2:
                    updates["current_city"] = city_state[0]
                    updates["current_state"] = city_state[1]

        if not updates:
            return LinkedInEnrichmentResult(
                status="failed",
                message="Search provider returned no usable profile fields.",
                provider_metadata=metadata,
            )

        return LinkedInEnrichmentResult(
            status="partial",
            message="LinkedIn enrichment completed from indexed public profile data.",
            updates=updates,
            provider_metadata=metadata,
        )


def _candidate_payloads(payload: Dict[str, Any]) -> list[Dict[str, Any]]:
    queue: list[Dict[str, Any]] = [payload]
    nested_keys = [
        "data",
        "result",
        "payload",
        "profile",
        "person",
        "user",
    ]

    for key in nested_keys:
        value = payload.get(key)
        if isinstance(value, dict):
            queue.append(value)

    results = payload.get("results")
    if isinstance(results, list):
        for item in results:
            if isinstance(item, dict):
                queue.append(item)

    deduped: list[Dict[str, Any]] = []
    seen_ids: set[int] = set()
    for item in queue:
        marker = id(item)
        if marker in seen_ids:
            continue
        seen_ids.add(marker)
        deduped.append(item)
    return deduped


def _extract_photo_url(candidate_payloads: list[Dict[str, Any]]) -> str:
    direct_keys = [
        "profile_photo_url",
        "profile_pic_url",
        "photo_url",
        "profilePictureUrl",
        "profile_picture_url",
        "avatar_url",
        "image_url",
    ]
    for payload in candidate_payloads:
        for key in direct_keys:
            value = _clean(payload.get(key))
            if value.startswith("http://") or value.startswith("https://"):
                return value

    nested_keys = ["profile_picture", "profilePicture", "photo", "image", "picture"]
    nested_url_keys = [
        "url",
        "image",
        "display_image_url",
        "displayImage",
        "display_image",
        "original",
        "large",
    ]
    for payload in candidate_payloads:
        for key in nested_keys:
            nested = payload.get(key)
            if isinstance(nested, dict):
                for nested_key in nested_url_keys:
                    value = _clean(nested.get(nested_key))
                    if value.startswith("http://") or value.startswith("https://"):
                        return value
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        for nested_key in nested_url_keys:
                            value = _clean(item.get(nested_key))
                            if value.startswith("http://") or value.startswith("https://"):
                                return value
    return ""


def _extract_experience_rows(candidate_payloads: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    rows: list[Dict[str, Any]] = []
    experience_keys = ["experiences", "experience", "positions", "work_experience"]
    for payload in candidate_payloads:
        for key in experience_keys:
            value = payload.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        rows.append(item)
    return rows


def _is_current_experience(row: Dict[str, Any]) -> bool:
    for key in ["is_current", "current", "isCurrent"]:
        value = row.get(key)
        if isinstance(value, bool) and value:
            return True
        if _clean(value).lower() in {"true", "yes", "1"}:
            return True

    for key in ["ends_at", "end_date", "endDate", "to", "end"]:
        value = row.get(key)
        text = _clean(value).lower()
        if not text:
            return True
        if any(word in text for word in ["present", "current", "now"]):
            return True
    return False


def _parse_headline_company_title(text: str) -> tuple[str, str]:
    cleaned = _clean(text)
    if not cleaned:
        return "", ""
    match = re.search(
        r"(?P<title>.+?)\s+at\s+(?P<company>[A-Za-z0-9&,. \-]{2,})",
        cleaned,
        flags=re.IGNORECASE,
    )
    if not match:
        return "", ""
    title = _clean(match.group("title"))
    company = _clean(match.group("company"))
    return title, company


def _extract_updates(payload: Dict[str, Any]) -> Dict[str, Any]:
    candidate_payloads = _candidate_payloads(payload)
    updates: Dict[str, Any] = {}

    photo = _extract_photo_url(candidate_payloads)
    if photo:
        updates["profile_photo_url"] = photo

    company = ""
    title = ""
    location = ""
    city = ""
    state = ""
    headline = ""

    for candidate in candidate_payloads:
        if not company:
            company = _first_non_empty(
                candidate,
                [
                    "current_company",
                    "company",
                    "occupation_company_name",
                    "company_name",
                    "employer",
                    "organization",
                ],
            )
        if not title:
            title = _first_non_empty(
                candidate,
                [
                    "current_job_title",
                    "job_title",
                    "title",
                    "occupation",
                ],
            )
        if not headline:
            headline = _first_non_empty(candidate, ["headline", "tagline", "summary_title"])
        if not location:
            location = _first_non_empty(
                candidate,
                [
                    "current_location",
                    "location",
                    "location_name",
                    "geo_location_name",
                ],
            )
        if not city:
            city = _first_non_empty(candidate, ["current_city", "city"])
        if not state:
            state = _first_non_empty(candidate, ["current_state", "state", "region"])

        if not location:
            location_value = candidate.get("location")
            if isinstance(location_value, dict):
                location = _first_non_empty(location_value, ["name", "display", "formatted"])
                if not city:
                    city = _first_non_empty(location_value, ["city"])
                if not state:
                    state = _first_non_empty(location_value, ["state", "region"])

    experience_rows = _extract_experience_rows(candidate_payloads)
    current_rows = [row for row in experience_rows if _is_current_experience(row)]
    selected_row = current_rows[0] if current_rows else (experience_rows[0] if experience_rows else None)
    if selected_row:
        if not company:
            company = _first_non_empty(selected_row, ["company", "company_name", "organization", "employer"])
        if not title:
            title = _first_non_empty(selected_row, ["title", "occupation", "job_title", "role"])
        if not location:
            location = _first_non_empty(selected_row, ["location", "location_name", "geo_location_name"])

    inferred_title, inferred_company = _parse_headline_company_title(headline)
    if not title and inferred_title:
        title = inferred_title
    if not company and inferred_company:
        company = inferred_company

    if company:
        updates["current_company"] = company
    if title:
        updates["current_job_title"] = title
    if city:
        updates["current_city"] = city
    if state:
        updates["current_state"] = state
    if location:
        updates["current_location"] = location
    elif city or state:
        updates["current_location"] = ", ".join(part for part in [city, state] if part)

    cleaned = {key: value for key, value in updates.items() if _clean(value)}
    LOG.info(
        "linkedin_extract_updates extracted_fields=%s",
        sorted(cleaned.keys()),
    )
    return cleaned


class LinkedInEnrichmentService:
    def __init__(
        self,
        *,
        provider: LinkedInEnrichmentProvider,
        min_interval_seconds: int = 30,
    ) -> None:
        self._provider = provider
        self._min_interval_seconds = max(0, int(min_interval_seconds))
        self._last_attempts: Dict[str, float] = {}

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def min_interval_seconds(self) -> int:
        return self._min_interval_seconds

    def config(self) -> Dict[str, Any]:
        disabled_reason = ""
        if isinstance(self._provider, DisabledLinkedInEnrichmentProvider):
            disabled_reason = self._provider.reason
        return {
            "enabled": self._provider.name != "disabled",
            "provider": self._provider.name,
            "disabled_reason": disabled_reason,
            "min_interval_seconds": self._min_interval_seconds,
        }

    def enrich_for_mentor(self, mentor_id: str, linkedin_url: str) -> LinkedInEnrichmentResult:
        raw_linkedin_url = _clean(linkedin_url)
        if not raw_linkedin_url:
            return LinkedInEnrichmentResult(
                status="failed",
                message="Mentor does not have a LinkedIn URL.",
            )

        normalized_url, normalize_error = normalize_linkedin_profile_url(raw_linkedin_url)
        if normalize_error:
            return LinkedInEnrichmentResult(
                status="failed",
                message=normalize_error,
                provider_metadata={
                    "provider": self._provider.name,
                    "requested_url": raw_linkedin_url,
                },
            )

        LOG.info(
            "linkedin_url_normalized mentor_id=%s provider=%s requested_url=%s normalized_url=%s",
            mentor_id,
            self._provider.name,
            raw_linkedin_url,
            normalized_url,
        )

        if self._provider.name == "disabled":
            result = self._provider.enrich(normalized_url)
            if not isinstance(result.provider_metadata, dict):
                result.provider_metadata = {}
            result.provider_metadata.setdefault("requested_url", raw_linkedin_url)
            result.provider_metadata.setdefault("normalized_url", normalized_url)
            return result

        if self._min_interval_seconds > 0:
            now = time.time()
            last_attempt = self._last_attempts.get(mentor_id, 0.0)
            elapsed = now - last_attempt
            if elapsed < self._min_interval_seconds:
                wait_seconds = int(self._min_interval_seconds - elapsed)
                return LinkedInEnrichmentResult(
                    status="throttled",
                    message=f"Please wait {max(wait_seconds, 1)}s before retrying enrichment for this mentor.",
                    provider_metadata={
                        "provider": self._provider.name,
                        "requested_url": raw_linkedin_url,
                        "normalized_url": normalized_url,
                    },
                )
            self._last_attempts[mentor_id] = now

        result = self._provider.enrich(normalized_url)
        if not isinstance(result.provider_metadata, dict):
            result.provider_metadata = {}
        result.provider_metadata.setdefault("provider", self._provider.name)
        result.provider_metadata.setdefault("requested_url", raw_linkedin_url)
        result.provider_metadata.setdefault("normalized_url", normalized_url)

        # Best-effort photo enrichment fallback for providers that do not return photos.
        has_photo = bool(_clean(result.updates.get("profile_photo_url")))
        if result.status not in {"disabled", "throttled"} and not has_photo:
            photo_timeout_seconds = float(
                os.getenv("WRAPPER_LINKEDIN_PUBLIC_PHOTO_TIMEOUT_SECONDS", "8")
            )
            photo_url, photo_metadata = _resolve_public_profile_photo_url(
                normalized_url,
                timeout_seconds=max(1.0, photo_timeout_seconds),
            )
            result.provider_metadata["public_photo_lookup"] = photo_metadata
            if photo_url:
                result.updates["profile_photo_url"] = photo_url
                if result.status in {"failed"}:
                    result.status = "partial"
                    result.message = (
                        "LinkedIn enrichment completed with partial profile data."
                    )
                LOG.info(
                    "linkedin_public_photo_applied mentor_id=%s provider=%s photo_url=%s",
                    mentor_id,
                    self._provider.name,
                    photo_url,
                )

        if result.status == "success":
            expected_fields = {
                "profile_photo_url",
                "current_company",
                "current_job_title",
                "current_location",
                "current_city",
                "current_state",
            }
            present = len([field for field in expected_fields if _clean(result.updates.get(field))])
            if 0 < present < len(expected_fields):
                result.status = "partial"
                result.message = (
                    result.message
                    if result.message
                    else "LinkedIn enrichment completed with partial profile data."
                )
        LOG.info(
            "linkedin_enrichment_result mentor_id=%s provider=%s status=%s update_fields=%s",
            mentor_id,
            self._provider.name,
            result.status,
            sorted(result.updates.keys()),
        )
        return result


def build_linkedin_enrichment_service_from_env() -> LinkedInEnrichmentService:
    enabled = _env_flag("WRAPPER_LINKEDIN_ENRICHMENT_ENABLED", True)
    provider_name = os.getenv("WRAPPER_LINKEDIN_ENRICHMENT_PROVIDER", "auto").strip().lower()
    min_interval = int(os.getenv("WRAPPER_LINKEDIN_ENRICH_MIN_INTERVAL_SECONDS", "0"))
    timeout_seconds = float(os.getenv("WRAPPER_LINKEDIN_ENRICHMENT_TIMEOUT_SECONDS", "20"))
    hard_disable = _env_flag("WRAPPER_LINKEDIN_ENRICHMENT_HARD_DISABLE", False)
    proxycurl_api_key = os.getenv("WRAPPER_LINKEDIN_PROXYCURL_API_KEY", "").strip()
    http_base_url = os.getenv("WRAPPER_LINKEDIN_PROVIDER_BASE_URL", "").strip()
    http_api_key = os.getenv("WRAPPER_LINKEDIN_PROVIDER_API_KEY", "")

    if hard_disable:
        provider: LinkedInEnrichmentProvider = DisabledLinkedInEnrichmentProvider(
            "LinkedIn enrichment is hard-disabled by configuration.",
        )
        return LinkedInEnrichmentService(provider=provider, min_interval_seconds=min_interval)

    if not enabled:
        provider = DisabledLinkedInEnrichmentProvider(
            "LinkedIn enrichment is disabled by WRAPPER_LINKEDIN_ENRICHMENT_ENABLED.",
        )
        return LinkedInEnrichmentService(provider=provider, min_interval_seconds=min_interval)

    if provider_name in {"", "auto"}:
        if proxycurl_api_key:
            provider = ProxycurlLinkedInEnrichmentProvider(
                api_key=proxycurl_api_key,
                timeout_seconds=timeout_seconds,
            )
        elif http_base_url:
            provider = HttpLinkedInEnrichmentProvider(
                base_url=http_base_url,
                api_key=http_api_key,
                timeout_seconds=timeout_seconds,
            )
        else:
            provider = DuckDuckGoLinkedInEnrichmentProvider(
                timeout_seconds=timeout_seconds,
            )
    elif provider_name == "mock":
        provider = MockLinkedInEnrichmentProvider()
    elif provider_name in {"search", "duckduckgo"}:
        provider = DuckDuckGoLinkedInEnrichmentProvider(
            timeout_seconds=timeout_seconds,
        )
    elif provider_name == "proxycurl":
        if proxycurl_api_key:
            provider = ProxycurlLinkedInEnrichmentProvider(
                api_key=proxycurl_api_key,
                timeout_seconds=timeout_seconds,
            )
        else:
            provider = DisabledLinkedInEnrichmentProvider(
                "Proxycurl provider selected, but WRAPPER_LINKEDIN_PROXYCURL_API_KEY is missing.",
            )
    elif provider_name == "http":
        if http_base_url:
            provider = HttpLinkedInEnrichmentProvider(
                base_url=http_base_url,
                api_key=http_api_key,
                timeout_seconds=timeout_seconds,
            )
        else:
            provider = DisabledLinkedInEnrichmentProvider(
                "HTTP provider selected, but WRAPPER_LINKEDIN_PROVIDER_BASE_URL is missing.",
            )
    elif provider_name == "disabled":
        provider = DisabledLinkedInEnrichmentProvider(
            "LinkedIn enrichment provider is set to disabled.",
        )
    else:
        provider = DisabledLinkedInEnrichmentProvider(
            f"Unknown LinkedIn provider '{provider_name}'.",
        )

    LOG.info(
        "linkedin_provider_initialized provider=%s enabled_flag=%s hard_disable=%s requested_provider=%s",
        provider.name,
        enabled,
        hard_disable,
        provider_name or "auto",
    )
    return LinkedInEnrichmentService(provider=provider, min_interval_seconds=min_interval)
