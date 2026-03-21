# fetch_aircraft_wikipedia.py
# Fetches 1000+ aircraft from Wikipedia and appends to aircraft.csv
# Uses Wikipedia API - all data sourced from Wikipedia
# Run: python fetch_aircraft_wikipedia.py
# Tim Fraser

"""
Fetches aircraft data from Wikipedia list pages and the Wikipedia API.
All entries are legitimately sourced from Wikipedia article summaries (extracts).
"""

import csv
import re
import time
import urllib.parse
import urllib.request

# Wikipedia API base URL
API_URL = "https://en.wikipedia.org/w/api.php"

# List pages to scrape for aircraft names (Wikipedia List of aircraft structure)
# These pages contain links to individual aircraft articles
LIST_PAGES = [
    "List of aircraft by date and usage category",
    "List of aircraft (0–Ah)",
    "List of aircraft (Ai–Am)",
    "List of aircraft (An–Az)",
    "List of aircraft (B–Be)",
    "List of aircraft (Bf–Bo)",
    "List of aircraft (Br–Bz)",
    "List of aircraft (C–Cc)",
    "List of aircraft (F)",
    "List of aircraft (M–Ma)",
]


def fetch_wikipedia_api(params: dict) -> dict:
    """Call Wikipedia API and return JSON response."""
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(API_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", "AircraftRAG/1.0 (Educational project; Python)")
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode()


def get_page_content(title: str) -> str:
    """Get wikitext content of a Wikipedia page."""
    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
        "formatversion": "2",
    }
    import json
    resp = json.loads(fetch_wikipedia_api(params))
    pages = resp.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        return ""
    revisions = pages[0].get("revisions", [])
    if not revisions:
        return ""
    return revisions[0].get("slots", {}).get("main", {}).get("content", "")


def extract_aircraft_links(wikitext: str) -> set:
    """Extract Wikipedia article titles from wikitext links. Skips redlinks."""
    # Match [[Article]] or [[Article|Display]] or [https://en.wikipedia.org/wiki/Article Name]
    # Skip edit, redlink, special pages
    pattern = r"\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]"
    matches = re.findall(pattern, wikitext)
    articles = set()
    skip_prefixes = ("Wikipedia:", "Category:", "File:", "Template:", "List of ", "User:")
    skip_exact = ("Aircraft", "Lists of aircraft", "edit", "redlink=1")
    for m in matches:
        title = m.strip()
        if not title or any(title.startswith(p) for p in skip_prefixes):
            continue
        if title in skip_exact or "list of" in title.lower():
            continue
        if "redlink" in title.lower() or "action=edit" in title.lower():
            continue
        # Skip very short or generic names
        if len(title) < 3:
            continue
        articles.add(title)
    return articles


def get_extract(title: str, sentences: int = 3) -> str:
    """Get article summary (extract) from Wikipedia API."""
    params = {
        "action": "query",
        "titles": title,
        "prop": "extracts",
        "exintro": "1",
        "explaintext": "1",
        "exsentences": str(sentences),
        "format": "json",
        "formatversion": "2",
    }
    import json
    resp = json.loads(fetch_wikipedia_api(params))
    pages = resp.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        return ""
    return pages[0].get("extract", "").strip()


def get_extracts_batch(titles: list, sentences: int = 2) -> dict:
    """Get extracts for up to 50 titles in one API call. Returns {title: extract}."""
    import json
    if not titles:
        return {}
    titles_str = "|".join(titles[:50])
    params = {
        "action": "query",
        "titles": titles_str,
        "prop": "extracts",
        "exintro": "1",
        "explaintext": "1",
        "exsentences": str(sentences),
        "format": "json",
        "formatversion": "2",
    }
    resp = json.loads(fetch_wikipedia_api(params))
    result = {}
    for page in resp.get("query", {}).get("pages", []):
        if "missing" in page:
            continue
        result[page.get("title", "")] = page.get("extract", "").strip()
    return result


def infer_type_from_title(title: str, section_hint: str = "") -> str:
    """Infer aircraft type from title or section. Returns generic type for CSV."""
    t = title.upper()
    s = section_hint.upper()
    if "FIGHTER" in s or "FIGHTER" in t or "F-" in t or "MIG-" in t or "MIRAGE" in t:
        return "fighter"
    if "BOMBER" in s or "BOMBER" in t or "B-" in t:
        return "bomber"
    if "TRANSPORT" in s or "C-" in t or "C130" in t or "C-17" in t or "C-5" in t:
        return "transport"
    if "RECON" in s or "U-2" in t or "SR-71" in t or "RECON" in t:
        return "reconnaissance"
    if "ATTACK" in s or "A-" in t or "A10" in t or "HARRIER" in t:
        return "attack"
    if "HELICOPTER" in s or "AH-" in t or "UH-" in t or "CH-" in t:
        return "helicopter"
    if "TRAINER" in s or "T-" in t:
        return "trainer"
    if "BOEING 7" in t or "AIRBUS" in t or "AIRLINER" in s or "COMMERCIAL" in s:
        return "airliner"
    if "DRONE" in t or "UAV" in t or "RQ-" in t or "MQ-" in t:
        return "UAV"
    # Default for civil/general
    if any(x in s for x in ["CIVIL", "AIR TRANSPORT", "GENERAL"]):
        return "airliner" if "TRANSPORT" in s else "general aviation"
    return "aircraft"


def infer_era_from_title(title: str) -> str:
    """Very rough era hint from designation patterns."""
    t = title.upper()
    if "F-35" in t or "F-22" in t or "B-2" in t:
        return "5th generation (2000s-present)"
    if "F-16" in t or "F-15" in t or "B-52" in t:
        return "4th generation / Cold War"
    if "SPITFIRE" in t or "Bf 109" in t or "MUSTANG" in t:
        return "WWII"
    if "707" in t or "747" in t or "DC-" in t:
        return "Jet age (1960s-1990s)"
    return "Various"


def main():
    import json
    import os

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "aircraft.csv")
    existing_path = os.path.join(script_dir, "aircraft.csv")

    # Collect aircraft from list pages - prioritize date/usage (has famous aircraft first)
    all_articles = []
    seen = set()
    print("Fetching aircraft lists from Wikipedia...")
    for page_title in LIST_PAGES:
        print(f"  - {page_title}")
        try:
            content = get_page_content(page_title)
            articles = extract_aircraft_links(content)
            for a in sorted(articles):
                if a not in seen:
                    seen.add(a)
                    all_articles.append(a)
            time.sleep(0.5)  # Be polite to Wikipedia
        except Exception as e:
            print(f"    Error: {e}")
            continue

    # Process up to 8000 articles to get 1000 with valid extracts
    articles_list = all_articles[:8000]
    print(f"\nFound {len(all_articles)} unique aircraft. Processing up to {len(articles_list)} (batches of 50)...")

    # Load existing rows to preserve
    existing_rows = []
    existing_names = set()
    if os.path.exists(existing_path):
        with open(existing_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_rows.append(row)
                existing_names.add(row["name"])

    # Build new rows using batch API
    new_rows = []
    batch_size = 50
    min_extract_len = 20
    for i in range(0, len(articles_list), batch_size):
        if len(new_rows) >= 1000:
            break
        batch = articles_list[i : i + batch_size]
        # Filter out existing
        batch = [t for t in batch if t not in existing_names]
        if not batch:
            continue
        if (i + batch_size) % 500 == 0 or i == 0:
            print(f"  Progress: {i+batch_size}/{len(articles_list)}, new: {len(new_rows)}")
        try:
            extracts = get_extracts_batch(batch, sentences=2)
            for title, extract in extracts.items():
                if len(new_rows) >= 1000:
                    break
                if not extract or len(extract) < min_extract_len:
                    continue
                if title in existing_names:
                    continue
                atype = infer_type_from_title(title)
                era = infer_era_from_title(title)
                short_desc = extract[:400] + "..." if len(extract) > 400 else extract
                new_rows.append({
                    "name": title,
                    "type": atype,
                    "era": era,
                    "mission": atype,
                    "key_features": short_desc[:200],
                    "design_philosophy": "Wikipedia-sourced",
                    "short_description": short_desc,
                })
                existing_names.add(title)
        except Exception as e:
            print(f"    Batch error: {e}")
        time.sleep(0.3)  # Rate limit

    # Merge and write
    fieldnames = ["name", "type", "era", "mission", "key_features", "design_philosophy", "short_description"]
    all_rows = existing_rows + new_rows
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nDone. Wrote {len(all_rows)} aircraft to {output_path}")
    print(f"  - Existing: {len(existing_rows)}")
    print(f"  - New from Wikipedia: {len(new_rows)}")


if __name__ == "__main__":
    main()
