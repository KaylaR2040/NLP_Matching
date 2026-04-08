from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List, Set

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


def pull_concentrations() -> List[str]:
    values: Set[str] = set(DEFAULT_CONCENTRATIONS)
    headers = {"User-Agent": "Mozilla/5.0"}

    for url in SOURCE_URLS:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        values.update(_extract_from_html(response.text))

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
