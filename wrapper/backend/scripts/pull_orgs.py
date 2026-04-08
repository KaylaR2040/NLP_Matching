from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Dict, List, Set

import requests


BASE_URL = "https://getinvolved.ncsu.edu/api/discovery/search/organizations"


def pull_organizations() -> List[str]:
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0"}

    all_orgs: List[Dict[str, object]] = []
    seen_ids: Set[str] = set()

    skip = 0
    top = 50
    page = 0
    stuck_pages = 0
    max_stuck_pages = 3

    while True:
        page += 1
        params = {
            "orderBy[0]": "UpperName asc",
            "top": top,
            "skip": skip,
            "query": "",
            "filter": "",
        }

        response = session.get(BASE_URL, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        items = data.get("value") or data.get("items") or []
        total_count = data.get("count") or data.get("total")

        print(
            f"[page {page}] skip={skip}, top={top} -> {len(items)} items"
            + (f" (total={total_count})" if total_count is not None else "")
        )

        if not items:
            print("No items returned; stopping.")
            break

        new_items = 0
        for org in items:
            oid = str(org.get("id") or org.get("Id") or org.get("_id") or "").strip()
            if not oid:
                all_orgs.append(org)
                new_items += 1
                continue
            if oid not in seen_ids:
                seen_ids.add(oid)
                all_orgs.append(org)
                new_items += 1

        print(f"         new unique this page: {new_items} | total unique: {len(all_orgs)}")

        if new_items == 0:
            stuck_pages += 1
            if stuck_pages >= max_stuck_pages:
                print("         Repeated pages detected; stopping.")
                break
        else:
            stuck_pages = 0

        skip += len(items)
        if total_count is not None and len(all_orgs) >= int(total_count):
            print("Reached reported total count; stopping.")
            break

        time.sleep(0.25)

    names: Set[str] = set()
    for org in all_orgs:
        name = str(org.get("name") or org.get("Name") or org.get("UpperName") or "").strip()
        if name:
            names.add(" ".join(name.split()))
    return sorted(names, key=lambda value: value.lower())


def main() -> None:
    parser = argparse.ArgumentParser(description="Pull NCSU organizations and write ncsu_orgs.txt")
    parser.add_argument("--output", required=True, help="Output file path")
    args = parser.parse_args()

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    names = pull_organizations()
    output_path.write_text("\n".join(names) + "\n", encoding="utf-8")
    print(f"Saved {len(names)} organizations to {output_path}")


if __name__ == "__main__":
    main()
