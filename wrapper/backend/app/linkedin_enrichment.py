from __future__ import annotations

import logging
import os
import time
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
        city = os.getenv("WRAPPER_LINKEDIN_MOCK_CITY", "Raleigh")
        state = os.getenv("WRAPPER_LINKEDIN_MOCK_STATE", "NC")
        updates = {
            "profile_photo_url": f"https://images.example.com/linkedin/{slug}.jpg",
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


def _extract_updates(payload: Dict[str, Any]) -> Dict[str, Any]:
    updates: Dict[str, Any] = {}

    photo = _first_non_empty(
        payload,
        [
            "profile_photo_url",
            "profile_pic_url",
            "photo_url",
            "profilePictureUrl",
        ],
    )
    if photo:
        updates["profile_photo_url"] = photo

    company = _first_non_empty(
        payload,
        [
            "current_company",
            "company",
            "occupation_company_name",
            "company_name",
        ],
    )
    title = _first_non_empty(
        payload,
        [
            "current_job_title",
            "title",
            "occupation",
            "headline",
        ],
    )
    location = _first_non_empty(
        payload,
        [
            "current_location",
            "location",
            "location_name",
        ],
    )
    city = _first_non_empty(payload, ["current_city", "city"])
    state = _first_non_empty(payload, ["current_state", "state", "region"])

    experiences = payload.get("experiences")
    if isinstance(experiences, list) and experiences:
        current_exp = experiences[0] if isinstance(experiences[0], dict) else {}
        if isinstance(current_exp, dict):
            if not company:
                company = _first_non_empty(current_exp, ["company", "company_name"])
            if not title:
                title = _first_non_empty(current_exp, ["title", "occupation"])
            if not location:
                location = _first_non_empty(current_exp, ["location"])

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

    return {key: value for key, value in updates.items() if _clean(value)}


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

    def enrich_for_mentor(self, mentor_id: str, linkedin_url: str) -> LinkedInEnrichmentResult:
        linkedin_url = _clean(linkedin_url)
        if not linkedin_url:
            return LinkedInEnrichmentResult(
                status="failed",
                message="Mentor does not have a LinkedIn URL.",
            )

        if self._min_interval_seconds > 0:
            now = time.time()
            last_attempt = self._last_attempts.get(mentor_id, 0.0)
            elapsed = now - last_attempt
            if elapsed < self._min_interval_seconds:
                wait_seconds = int(self._min_interval_seconds - elapsed)
                return LinkedInEnrichmentResult(
                    status="throttled",
                    message=f"Please wait {max(wait_seconds, 1)}s before retrying enrichment for this mentor.",
                )
            self._last_attempts[mentor_id] = now

        result = self._provider.enrich(linkedin_url)
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
        return result


def build_linkedin_enrichment_service_from_env() -> LinkedInEnrichmentService:
    enabled = _env_flag("WRAPPER_LINKEDIN_ENRICHMENT_ENABLED", False)
    provider_name = os.getenv("WRAPPER_LINKEDIN_ENRICHMENT_PROVIDER", "disabled").strip().lower()
    min_interval = int(os.getenv("WRAPPER_LINKEDIN_ENRICH_MIN_INTERVAL_SECONDS", "30"))

    if not enabled:
        provider: LinkedInEnrichmentProvider = DisabledLinkedInEnrichmentProvider(
            "LinkedIn enrichment is disabled by configuration.",
        )
        return LinkedInEnrichmentService(provider=provider, min_interval_seconds=min_interval)

    if provider_name == "mock":
        provider = MockLinkedInEnrichmentProvider()
    elif provider_name == "proxycurl":
        api_key = os.getenv("WRAPPER_LINKEDIN_PROXYCURL_API_KEY", "").strip()
        if not api_key:
            provider = DisabledLinkedInEnrichmentProvider(
                "Proxycurl provider selected, but WRAPPER_LINKEDIN_PROXYCURL_API_KEY is missing.",
            )
        else:
            provider = ProxycurlLinkedInEnrichmentProvider(
                api_key=api_key,
                timeout_seconds=float(os.getenv("WRAPPER_LINKEDIN_ENRICHMENT_TIMEOUT_SECONDS", "20")),
            )
    elif provider_name == "http":
        provider = HttpLinkedInEnrichmentProvider(
            base_url=os.getenv("WRAPPER_LINKEDIN_PROVIDER_BASE_URL", ""),
            api_key=os.getenv("WRAPPER_LINKEDIN_PROVIDER_API_KEY", ""),
            timeout_seconds=float(os.getenv("WRAPPER_LINKEDIN_ENRICHMENT_TIMEOUT_SECONDS", "20")),
        )
    else:
        provider = DisabledLinkedInEnrichmentProvider(
            "No supported LinkedIn provider is configured.",
        )

    LOG.info("linkedin_provider_initialized provider=%s enabled=%s", provider.name, enabled)
    return LinkedInEnrichmentService(provider=provider, min_interval_seconds=min_interval)

