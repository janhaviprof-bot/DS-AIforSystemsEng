# fetch_aircraft_wikidata.py
# Fetches 1000+ aircraft from Wikidata (Wikipedia's structured data sister project)
# All data is sourced from Wikidata which links to Wikipedia articles
# Run: python fetch_aircraft_wikidata.py
# Tim Fraser

"""
Fetches aircraft from Wikidata SPARQL endpoint. Wikidata is Wikipedia's structured
database - all items have links to Wikipedia articles. No rate limits for SPARQL.
"""

import csv
import json
import os
import urllib.parse
import urllib.request

# Wikidata Query Service
SPARQL_URL = "https://query.wikidata.org/sparql"

# Query: 1000 aircraft with English label, description, and specs
# Q11436 = aircraft; P176=manufacturer, P606=first flight, P730=service retirement,
# P2073=range, P2217=cruise speed, P2052=speed, P1083=capacity, P2043=length, P2050=wingspan
QUERY = """
SELECT ?item ?itemLabel ?description ?typeLabel ?manufacturerLabel ?firstFlight
       ?serviceRetirement ?range ?cruiseSpeed ?maxSpeed ?capacity ?length ?wingspan
WHERE {
  ?item wdt:P31/wdt:P279* wd:Q11436.
  ?item rdfs:label ?itemLabel.
  FILTER(LANG(?itemLabel) = "en")
  OPTIONAL { ?item schema:description ?description. FILTER(LANG(?description) = "en") }
  OPTIONAL { ?item wdt:P31 ?type. ?type rdfs:label ?typeLabel. FILTER(LANG(?typeLabel) = "en") }
  OPTIONAL { ?item wdt:P176 ?manufacturer. ?manufacturer rdfs:label ?manufacturerLabel. FILTER(LANG(?manufacturerLabel) = "en") }
  OPTIONAL { ?item wdt:P606 ?firstFlight }
  OPTIONAL { ?item wdt:P730 ?serviceRetirement }
  OPTIONAL { ?item wdt:P2073 ?range }
  OPTIONAL { ?item wdt:P2217 ?cruiseSpeed }
  OPTIONAL { ?item wdt:P2052 ?maxSpeed }
  OPTIONAL { ?item wdt:P1083 ?capacity }
  OPTIONAL { ?item wdt:P2043 ?length }
  OPTIONAL { ?item wdt:P2050 ?wingspan }
} LIMIT 1500
"""


def run_sparql(query: str) -> list:
    """Execute SPARQL query and return bindings."""
    params = {"query": query, "format": "json"}
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(SPARQL_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", "AircraftRAG/1.0 (Educational project; Python)")
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode())
    return result.get("results", {}).get("bindings", [])


def normalize_type(type_label: str) -> str:
    """Map Wikidata type to our CSV type."""
    if not type_label:
        return "aircraft"
    t = type_label.upper()
    if "FIGHTER" in t:
        return "fighter"
    if "BOMBER" in t:
        return "bomber"
    if "TRANSPORT" in t or "CARGO" in t:
        return "transport"
    if "RECON" in t or "SURVEILLANCE" in t:
        return "reconnaissance"
    if "ATTACK" in t or "STRIKE" in t:
        return "attack"
    if "HELICOPTER" in t:
        return "helicopter"
    if "TRAINER" in t:
        return "trainer"
    if "AIRLINER" in t or "PASSENGER" in t:
        return "airliner"
    if "DRONE" in t or "UAV" in t:
        return "UAV"
    return "aircraft"


# Unit conversion constants (Wikidata unit URIs contain entity IDs)
MI_TO_KM = 1.609
NMI_TO_KM = 1.852
KNOT_TO_KMH = 1.852
MPH_TO_KMH = 1.609
FT_TO_M = 0.3048


def _amount_and_unit(binding: dict) -> tuple[float | None, str | None]:
    """Extract amount and unit from a Wikidata quantity binding.
    SPARQL JSON can return: value as number/string, or value as JSON object with amount/unit.
    """
    if not binding:
        return None, None
    val = binding.get("value")
    unit = binding.get("unit", "")
    if isinstance(unit, dict):
        unit = unit.get("value", "") if isinstance(unit.get("value"), str) else ""
    if not isinstance(unit, str):
        unit = ""
    if val is None:
        return None, None
    if isinstance(val, (int, float)):
        return float(val), unit
    if isinstance(val, str):
        try:
            data = json.loads(val)
            if isinstance(data, dict):
                amt = data.get("amount", data.get("value", val))
                u = data.get("unit", unit)
                return float(str(amt).lstrip("+")), str(u) if u else unit
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        try:
            return float(val.lstrip("+-")), unit
        except (TypeError, ValueError):
            pass
    return None, None


def to_km(amount: float, unit_uri: str) -> float:
    """Convert distance to km."""
    if amount is None:
        return 0.0
    u = (unit_uri or "").lower()
    if "Q11573" in u or "metre" in u or "meter" in u:
        return amount / 1000.0 if "milli" in u else amount
    if "Q828224" in u or "kilometre" in u:
        return amount
    if "Q253276" in u or "mile" in u and "nautical" not in u:
        return amount * MI_TO_KM
    if "Q93318" in u or "nautical" in u:
        return amount * NMI_TO_KM
    if "Q3710" in u or "foot" in u or "feet" in u:
        return amount * FT_TO_M / 1000.0
    return amount  # assume km


def to_kmh(amount: float, unit_uri: str) -> float:
    """Convert speed to km/h."""
    if amount is None:
        return 0.0
    u = (unit_uri or "").lower()
    if "Q180154" in u or "kilometre" in u and "hour" in u:
        return amount
    if "Q128822" in u or "knot" in u:
        return amount * KNOT_TO_KMH
    if "Q211256" in u or "mile" in u and "hour" in u:
        return amount * MPH_TO_KMH
    if "Q182429" in u or "metre" in u and "second" in u:
        return amount * 3.6
    if "Q160669" in u or "mach" in u:
        return amount * 1225.0  # approx Mach 1 at 15°C
    return amount


def to_m(amount: float, unit_uri: str) -> float:
    """Convert length to metres."""
    if amount is None:
        return 0.0
    u = (unit_uri or "").lower()
    if "Q11573" in u or "metre" in u or "meter" in u:
        return amount
    if "Q3710" in u or "foot" in u or "feet" in u:
        return amount * FT_TO_M
    if "Q174728" in u or "centimetre" in u:
        return amount / 100.0
    return amount


def parse_quantity(binding: dict, converter) -> str:
    """Parse Wikidata quantity and return string for CSV (empty if missing)."""
    amt, unit = _amount_and_unit(binding)
    if amt is None:
        return ""
    try:
        val = converter(amt, unit or "")
        return str(int(val)) if val == int(val) else f"{val:.2f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return ""


def parse_year(binding: dict) -> str:
    """Extract year from Wikidata time value."""
    if not binding:
        return ""
    val = binding.get("value")
    if not val:
        return ""
    s = str(val)
    if s.startswith("+"):
        s = s[1:]
    parts = s.split("-")
    return parts[0] if parts else ""


# Known specs for 20 curated aircraft (Wikipedia-derived)
CURATED_BACKFILL = {
    "F-16 Fighting Falcon": {
        "manufacturer": "Lockheed Martin",
        "first_flight": "1974",
        "status": "Active",
        "range_km": "3900",
        "cruise_speed_kmh": "850",
        "max_speed_kmh": "2124",
        "capacity_passengers": "",
        "crew": "1",
        "length_m": "15.03",
        "wingspan_m": "9.96",
    },
    "F-22 Raptor": {
        "manufacturer": "Lockheed Martin",
        "first_flight": "1997",
        "status": "Active",
        "range_km": "2960",
        "cruise_speed_kmh": "1838",
        "max_speed_kmh": "2410",
        "capacity_passengers": "",
        "crew": "1",
        "length_m": "18.9",
        "wingspan_m": "13.56",
    },
    "Supermarine Spitfire": {
        "manufacturer": "Supermarine",
        "first_flight": "1936",
        "status": "Retired",
        "range_km": "760",
        "cruise_speed_kmh": "580",
        "max_speed_kmh": "717",
        "capacity_passengers": "",
        "crew": "1",
        "length_m": "9.12",
        "wingspan_m": "11.23",
    },
    "SR-71 Blackbird": {
        "manufacturer": "Lockheed",
        "first_flight": "1964",
        "status": "Retired",
        "range_km": "5400",
        "cruise_speed_kmh": "3060",
        "max_speed_kmh": "3540",
        "capacity_passengers": "",
        "crew": "2",
        "length_m": "32.74",
        "wingspan_m": "16.94",
    },
    "Lockheed U-2": {
        "manufacturer": "Lockheed",
        "first_flight": "1955",
        "status": "Active",
        "range_km": "10600",
        "cruise_speed_kmh": "690",
        "max_speed_kmh": "821",
        "capacity_passengers": "",
        "crew": "1",
        "length_m": "19.2",
        "wingspan_m": "31.4",
    },
    "F-117 Nighthawk": {
        "manufacturer": "Lockheed",
        "first_flight": "1981",
        "status": "Retired",
        "range_km": "1720",
        "cruise_speed_kmh": "684",
        "max_speed_kmh": "993",
        "capacity_passengers": "",
        "crew": "1",
        "length_m": "20.09",
        "wingspan_m": "13.2",
    },
    "B-52 Stratofortress": {
        "manufacturer": "Boeing",
        "first_flight": "1952",
        "status": "Active",
        "range_km": "14160",
        "cruise_speed_kmh": "844",
        "max_speed_kmh": "957",
        "capacity_passengers": "",
        "crew": "5",
        "length_m": "48.5",
        "wingspan_m": "56.4",
    },
    "A-10 Thunderbolt II": {
        "manufacturer": "Fairchild Republic",
        "first_flight": "1972",
        "status": "Active",
        "range_km": "3900",
        "cruise_speed_kmh": "560",
        "max_speed_kmh": "706",
        "capacity_passengers": "",
        "crew": "1",
        "length_m": "16.26",
        "wingspan_m": "17.53",
    },
    "Concorde": {
        "manufacturer": "BAC / Aerospatiale",
        "first_flight": "1969",
        "status": "Retired",
        "range_km": "7250",
        "cruise_speed_kmh": "2145",
        "max_speed_kmh": "2330",
        "capacity_passengers": "128",
        "crew": "3",
        "length_m": "61.66",
        "wingspan_m": "25.6",
    },
    "F-4 Phantom II": {
        "manufacturer": "McDonnell Douglas",
        "first_flight": "1958",
        "status": "Active",
        "range_km": "2600",
        "cruise_speed_kmh": "940",
        "max_speed_kmh": "2370",
        "capacity_passengers": "",
        "crew": "2",
        "length_m": "19.2",
        "wingspan_m": "11.7",
    },
    "B-2 Spirit": {
        "manufacturer": "Northrop Grumman",
        "first_flight": "1989",
        "status": "Active",
        "range_km": "11100",
        "cruise_speed_kmh": "900",
        "max_speed_kmh": "1010",
        "capacity_passengers": "",
        "crew": "2",
        "length_m": "21",
        "wingspan_m": "52.4",
    },
    "C-17 Globemaster III": {
        "manufacturer": "Boeing",
        "first_flight": "1991",
        "status": "Active",
        "range_km": "4480",
        "cruise_speed_kmh": "830",
        "max_speed_kmh": "833",
        "capacity_passengers": "102",
        "crew": "3",
        "length_m": "53",
        "wingspan_m": "51.75",
    },
    "Hawker Siddeley Harrier": {
        "manufacturer": "Hawker Siddeley",
        "first_flight": "1966",
        "status": "Retired",
        "range_km": "3425",
        "cruise_speed_kmh": "850",
        "max_speed_kmh": "1185",
        "capacity_passengers": "",
        "crew": "1",
        "length_m": "14.27",
        "wingspan_m": "7.7",
    },
    "F-15 Eagle": {
        "manufacturer": "McDonnell Douglas",
        "first_flight": "1972",
        "status": "Active",
        "range_km": "3900",
        "cruise_speed_kmh": "917",
        "max_speed_kmh": "2655",
        "capacity_passengers": "",
        "crew": "1",
        "length_m": "19.43",
        "wingspan_m": "13.05",
    },
    "F-14 Tomcat": {
        "manufacturer": "Grumman",
        "first_flight": "1970",
        "status": "Retired",
        "range_km": "2960",
        "cruise_speed_kmh": "740",
        "max_speed_kmh": "2485",
        "capacity_passengers": "",
        "crew": "2",
        "length_m": "19.1",
        "wingspan_m": "19.55",
    },
    "C-130 Hercules": {
        "manufacturer": "Lockheed Martin",
        "first_flight": "1954",
        "status": "Active",
        "range_km": "3800",
        "cruise_speed_kmh": "540",
        "max_speed_kmh": "592",
        "capacity_passengers": "92",
        "crew": "5",
        "length_m": "29.79",
        "wingspan_m": "40.41",
    },
    "MiG-21": {
        "manufacturer": "Mikoyan-Gurevich",
        "first_flight": "1955",
        "status": "Active",
        "range_km": "1210",
        "cruise_speed_kmh": "850",
        "max_speed_kmh": "2175",
        "capacity_passengers": "",
        "crew": "1",
        "length_m": "15.76",
        "wingspan_m": "7.15",
    },
    "Boeing 747": {
        "manufacturer": "Boeing",
        "first_flight": "1969",
        "status": "Active",
        "range_km": "14815",
        "cruise_speed_kmh": "913",
        "max_speed_kmh": "988",
        "capacity_passengers": "524",
        "crew": "3",
        "length_m": "76.3",
        "wingspan_m": "68.4",
    },
    "F-35 Lightning II": {
        "manufacturer": "Lockheed Martin",
        "first_flight": "2006",
        "status": "Active",
        "range_km": "2220",
        "cruise_speed_kmh": "1223",
        "max_speed_kmh": "1930",
        "capacity_passengers": "",
        "crew": "1",
        "length_m": "15.67",
        "wingspan_m": "10.7",
    },
    "C-5 Galaxy": {
        "manufacturer": "Lockheed Martin",
        "first_flight": "1968",
        "status": "Active",
        "range_km": "4440",
        "cruise_speed_kmh": "830",
        "max_speed_kmh": "932",
        "capacity_passengers": "345",
        "crew": "7",
        "length_m": "75.3",
        "wingspan_m": "67.89",
    },
    "Airbus A380": {
        "manufacturer": "Airbus",
        "first_flight": "2005",
        "status": "Active",
        "range_km": "15200",
        "cruise_speed_kmh": "903",
        "max_speed_kmh": "945",
        "capacity_passengers": "853",
        "crew": "2",
        "length_m": "72.72",
        "wingspan_m": "79.75",
    },
    "Boeing 737": {
        "manufacturer": "Boeing",
        "first_flight": "1967",
        "status": "Active",
        "range_km": "5670",
        "cruise_speed_kmh": "780",
        "max_speed_kmh": "946",
        "capacity_passengers": "215",
        "crew": "2",
        "length_m": "40",
        "wingspan_m": "35.8",
    },
}


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "aircraft.csv")

    print("Fetching 1000+ aircraft from Wikidata (Wikipedia's structured database)...")
    bindings = run_sparql(QUERY)

    # Deduplicate by item (same item can have multiple type bindings)
    seen = set()
    rows = []
    for b in bindings:
        item = b.get("item", {}).get("value", "")
        if item in seen:
            continue
        seen.add(item)
        label = b.get("itemLabel", {}).get("value", "")
        desc = b.get("description", {}).get("value", "")
        type_label = b.get("typeLabel", {}).get("value", "")
        if not label or len(label) < 2:
            continue
        atype = normalize_type(type_label)
        short_desc = desc if desc else f"Aircraft: {label}. Source: Wikidata (links to Wikipedia)."

        manufacturer = b.get("manufacturerLabel", {}).get("value", "")
        first_flight = parse_year(b.get("firstFlight", {}))
        service_ret = b.get("serviceRetirement", {})
        status = "Retired" if service_ret and service_ret.get("value") else (
            "Prototype" if "prototype" in (type_label or "").lower() else "Active"
        )
        range_km = parse_quantity(b.get("range", {}), to_km)
        cruise_speed_kmh = parse_quantity(b.get("cruiseSpeed", {}), to_kmh)
        max_speed_kmh = parse_quantity(b.get("maxSpeed", {}), to_kmh)
        capacity = ""
        cap_b = b.get("capacity", {})
        if cap_b:
            amt, _ = _amount_and_unit(cap_b)
            if amt is not None:
                capacity = str(int(amt))
        crew = ""  # Sparse in Wikidata; leave empty for v1
        length_m = parse_quantity(b.get("length", {}), to_m)
        wingspan_m = parse_quantity(b.get("wingspan", {}), to_m)

        rows.append({
            "name": label,
            "type": atype,
            "era": "Various",
            "mission": atype,
            "key_features": short_desc[:200],
            "design_philosophy": "Wikipedia-sourced via Wikidata",
            "short_description": short_desc[:500],
            "manufacturer": manufacturer,
            "first_flight": first_flight,
            "status": status,
            "range_km": range_km,
            "cruise_speed_kmh": cruise_speed_kmh,
            "max_speed_kmh": max_speed_kmh,
            "capacity_passengers": capacity,
            "crew": crew,
            "length_m": length_m,
            "wingspan_m": wingspan_m,
        })
        if len(rows) >= 1000:
            break

    # Load existing to merge (keep our 20 curated first)
    new_cols = [
        "manufacturer", "first_flight", "status", "range_km", "cruise_speed_kmh",
        "max_speed_kmh", "capacity_passengers", "crew", "length_m", "wingspan_m",
    ]
    existing_rows = []
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                for c in new_cols:
                    row.setdefault(c, "")
                existing_rows.append(row)

    # Merge: keep existing, add new (avoid duplicates by name)
    existing_names = {r["name"] for r in existing_rows}
    new_rows = [r for r in rows if r["name"] not in existing_names][:1000]
    all_rows = existing_rows + new_rows

    # Lookup: SPARQL spec data by name (for filling existing rows)
    sparql_by_name = {r["name"]: r for r in rows}

    # Fill spec fields: (1) curated backfill, (2) SPARQL data for empty fields
    for row in all_rows:
        name = row.get("name", "")
        # 1. Curated backfill (highest priority)
        if name in CURATED_BACKFILL:
            for key, val in CURATED_BACKFILL[name].items():
                if val and (not row.get(key) or row.get(key) == ""):
                    row[key] = val
        # 2. SPARQL data for any remaining empty spec fields
        if name in sparql_by_name:
            src = sparql_by_name[name]
            for key in new_cols:
                if not row.get(key) or row.get(key) == "":
                    val = src.get(key, "")
                    if val:
                        row[key] = val

    # Put spec columns after name/type so they're visible without scrolling
    fieldnames = [
        "name", "type", "manufacturer", "first_flight", "status", "range_km",
        "cruise_speed_kmh", "max_speed_kmh", "capacity_passengers", "crew",
        "length_m", "wingspan_m", "era", "mission", "key_features",
        "design_philosophy", "short_description",
    ]
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nDone. Wrote {len(all_rows)} aircraft to {output_path}")
    print(f"  - Existing: {len(existing_rows)}")
    print(f"  - New from Wikidata: {len(new_rows)}")
    print("  (Wikidata links to Wikipedia - all entries are Wikipedia-sourced)")


if __name__ == "__main__":
    main()
