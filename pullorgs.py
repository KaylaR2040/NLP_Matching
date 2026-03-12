import time
import requests

# TODO: write this code to pull from all of the different URLS for orgs, concentrations, grad school...
# TODO: Make it then push all of this info into the assets.. and make sure to write docs for this all so that it continutes being updated..  

BASE_URL = "https://getinvolved.ncsu.edu/api/discovery/search/organizations"

session = requests.Session()
headers = {"User-Agent": "Mozilla/5.0"}

all_orgs = []
skip = 0
top = 50                 # safer; many endpoints cap around 50
page = 0

seen_ids = set()
stuck_pages = 0
MAX_STUCK_PAGES = 3      # if we get repeats too many times, stop

while True:
    page += 1

    params = {
        "orderBy[0]": "UpperName asc",
        "top": top,
        "skip": skip,
        "query": "",
        "filter": ""
    }

    r = session.get(BASE_URL, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()

    items = data.get("value") or data.get("items") or []
    total_count = data.get("count") or data.get("total")  # may be None

    # Progress log header
    print(f"[page {page}] requested skip={skip}, top={top} -> got {len(items)} items"
          + (f" (total={total_count})" if total_count is not None else ""))

    if not items:
        print("No items returned; stopping.")
        break

    # Detect repeats / lack of progress
    new_items = 0
    for o in items:
        oid = o.get("id") or o.get("Id") or o.get("_id")
        if oid is None:
            # If there is no stable id, treat as new (can’t dedupe reliably)
            new_items += 1
            all_orgs.append(o)
            continue

        if oid not in seen_ids:
            seen_ids.add(oid)
            new_items += 1
            all_orgs.append(o)

    print(f"         new unique this page: {new_items} | total unique: {len(all_orgs)}")

    if new_items == 0:
        stuck_pages += 1
        print(f"         WARNING: page appears to repeat data (stuck_pages={stuck_pages}).")
        if stuck_pages >= MAX_STUCK_PAGES:
            print("         Too many repeated pages; stopping to avoid infinite loop.")
            break
    else:
        stuck_pages = 0

    # Advance skip by the number of items the server returned (paging)
    skip += len(items)

    # Optional: if API gives a total count, stop when reached/exceeded
    if total_count is not None and len(all_orgs) >= int(total_count):
        print("Reached reported total count; stopping.")
        break

    time.sleep(0.3)

print(f"Downloaded {len(all_orgs)} unique org records")

# Extract names safely
names = []
for o in all_orgs:
    name = o.get("name") or o.get("Name") or o.get("UpperName")
    if name:
        names.append(name)

with open("ncsu_orgs.txt", "w", encoding="utf-8") as f:
    for n in sorted(set(names)):
        f.write(n + "\n")

print("Saved ncsu_orgs.txt")
