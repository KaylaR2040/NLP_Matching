from __future__ import annotations

import argparse
import os
import re
import time
from pathlib import Path
from typing import List, Optional, Set

import requests
from bs4 import BeautifulSoup


SOURCE_URLS = [
    "https://ece.ncsu.edu/academics/undergraduate/electrical-engineering/",
    "https://ece.ncsu.edu/academics/undergraduate/computer-engineering/",
]

DEFAULT_CONCENTRATIONS = {
    "Artificial Intelligence and Machine Learning Concentration",
    "Computer Architecture and Emerging Systems Concentration",
    "Computer Systems Software Concentration",
    "Embedded Systems Concentration",
    "Networking Hardware Concentration",
    "Networking Software Concentration",
    "Analog Circuits Concentration",
    "Biomedical Instrumentation Concentration",
    "Communications and Signal Processing Concentration",
    "Controls and Robotics Concentration",
    "Digital Circuits Concentration",
    "Electronic Devices Concentration",
    "Music Technology Concentration",
    "Optics and Photonics Concentration",
    "Power Systems Concentration",
    "Radio Frequency Circuits Concentration",
    "Renewable Electric Energy Systems Concentration",
}


def _normalize_concentration(text: str) -> str:
    value = " ".join((text or "").split()).strip()
    if not value:
        return ""
    if ": " in value:
        value = value.split(": ", 1)[1].strip()
    if value.endswith("Concentrations"):
        value = value[:-1]
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _extract_from_html(html: str) -> Set[str]:
    soup = BeautifulSoup(html, "html.parser")
    results: Set[str] = set()
    for anchor in soup.find_all("a"):
        text = _normalize_concentration(anchor.get_text(" ", strip=True))
        if not text:
            continue
        if "Concentration" not in text:
            continue
        results.add(text)
    return results


def _fetch_html_with_retries(
    session: requests.Session,
    *,
    url: str,
    headers: dict,
    timeout_seconds: float,
    max_attempts: int,
    backoff_seconds: float,
) -> Optional[str]:
    last_error = ""
    for attempt in range(1, max_attempts + 1):
        try:
            response = session.get(url, headers=headers, timeout=timeout_seconds)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            last_error = str(exc)
            print(
                f"Warning: failed to pull concentrations from {url} "
                f"(attempt {attempt}/{max_attempts}): {last_error}"
            )
            if attempt < max_attempts:
                time.sleep(backoff_seconds * attempt)

    print(f"Warning: giving up on {url} after {max_attempts} attempts. Last error: {last_error}")
    return None


def pull_concentrations() -> List[str]:
    values: Set[str] = set(DEFAULT_CONCENTRATIONS)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MentorMatcher/1.0)"}
    timeout_seconds = float(os.getenv("WRAPPER_CONCENTRATIONS_HTTP_TIMEOUT_SECONDS", "8"))
    max_attempts = max(1, int(os.getenv("WRAPPER_CONCENTRATIONS_HTTP_MAX_ATTEMPTS", "2")))
    backoff_seconds = float(os.getenv("WRAPPER_CONCENTRATIONS_HTTP_BACKOFF_SECONDS", "1.0"))
    session = requests.Session()

    fetched_any = False
    for url in SOURCE_URLS:
        html = _fetch_html_with_retries(
            session,
            url=url,
            headers=headers,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            backoff_seconds=backoff_seconds,
        )
        if not html:
            continue
        fetched_any = True
        extracted = _extract_from_html(html)
        print(f"Pulled {len(extracted)} concentration candidates from {url}")
        values.update(extracted)

    if not fetched_any:
        print(
            "Warning: network sources were unavailable; using default concentrations list only."
        )

    return sorted({" ".join(item.split()).strip() for item in values if item}, key=lambda item: item.lower())


def main() -> None:
    parser = argparse.ArgumentParser(description="Pull ECE concentrations and write concentrations.txt")
    parser.add_argument("--output", required=True, help="Output file path")
    args = parser.parse_args()

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    concentrations = pull_concentrations()
    output_path.write_text("\n".join(concentrations) + "\n", encoding="utf-8")
    print(f"Saved {len(concentrations)} concentrations to {output_path}")


if __name__ == "__main__":
    main()
