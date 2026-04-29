# 01_ingest_traffic.py
# Ingest Brussels Realtime Traffic Counts (1m, t1)
# Pairs with 01_ingest_traffic.R
# Tim Fraser
#
# This cron-friendly script fetches the latest traverse-level vehicle counts from
# the Brussels traffic API and stores normalized rows in SQLite.

# Run from inside the 12_end/ directory so the paths resolve correctly.
# Git bash: cd 12_end && python 01_ingest_traffic.py
# Powershell: Set-Location 12_end; python 01_ingest_traffic.py

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests


# 1. CONFIG ###################################

# Brussels Traffic Vehicle Counts API documentation:
# https://data.mobility.brussels/traffic/api/counts/
BASE_URL = "https://data.mobility.brussels/traffic/api/counts/"
BRUSSELS_METRO_ID = 948
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DB_PATH = DATA_DIR / "traffic.db"
DATA_DIR.mkdir(parents=True, exist_ok=True)

print("\n====================================================")
print("01_ingest_traffic.py | Brussels realtime ingest")
print("====================================================")
print(f"   metro_id: {BRUSSELS_METRO_ID}")
print(f"   api: {BASE_URL}")


def get_with_retry(url: str, params: dict, max_attempts: int = 5, timeout: int = 30) -> requests.Response:
    """Fetch API payload with retry/backoff for transient failures."""
    for attempt in range(1, max_attempts + 1):
        response = requests.get(url, params=params, timeout=timeout)
        if response.status_code in {429, 500, 502, 503, 504} and attempt < max_attempts:
            retry_after = response.headers.get("Retry-After")
            sleep_seconds = int(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 30)
            print(
                f"   warning transient status={response.status_code}; "
                f"retrying in {sleep_seconds}s (attempt {attempt}/{max_attempts})"
            )
            time.sleep(sleep_seconds)
            continue
        response.raise_for_status()
        return response
    raise RuntimeError("Failed to fetch traffic payload after retries.")


def parse_bxl_time_to_utc(end_time: str) -> str | None:
    """Convert Brussels-local timestamp to UTC string format used in SQLite."""
    if not end_time:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M"):
        try:
            local_dt = datetime.strptime(end_time, fmt).replace(tzinfo=ZoneInfo("Europe/Brussels"))
            utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
            return utc_dt.strftime("%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            continue
    return None


# 2. FETCH DATA ###################################

# Ask the API for the "live" request payload at one-minute interval granularity.
response = get_with_retry(
    BASE_URL,
    params={"request": "live", "includeLanes": "false", "interval": "1"},
    timeout=30,
)
payload = response.json()
data = payload.get("data", {})

# Hard-fail fast if API returns an empty payload so the cron run is visibly red.
if not data:
    raise SystemExit("Brussels traffic API returned empty data payload.")

monitors = list(data.keys())
print(f"   monitors in payload: {len(monitors)}")


# 3. CLEAN DATA ###################################

# Convert nested monitor payloads into flat rows with expected schema and types.
rows = []
for monitor_id, monitor_payload in data.items():
    one_min = (monitor_payload.get("results", {}) or {}).get("1m", {}) or {}
    t1 = one_min.get("t1", {}) or {}
    vehicles = t1.get("count")
    speed = t1.get("speed")
    occupancy = t1.get("occupancy")
    observed_at_raw = t1.get("end_time", "")
    observed_at = parse_bxl_time_to_utc(observed_at_raw)

    # Skip malformed rows early to keep downstream SQL simple and robust.
    if vehicles is None or observed_at is None or not monitor_id:
        continue

    try:
        row = (
            BRUSSELS_METRO_ID,
            str(monitor_id),
            observed_at,
            int(vehicles),
            max(float(speed), 0.0) if speed is not None else None,
            float(occupancy) if occupancy is not None else None,
        )
        rows.append(row)
    except (TypeError, ValueError):
        continue

if not rows:
    raise SystemExit("No valid 1m/t1 monitor rows parsed from Brussels API payload.")

print(f"   parsed rows: {len(rows)}")
print(f"   sample row: {rows[0]}")


# 4. WRITE TO SQLITE ###################################

# Keep database logic intentionally minimal and easy to read for students.
conn = sqlite3.connect(str(DB_PATH))
conn.execute(
    """
    CREATE TABLE IF NOT EXISTS traffic (
      metro_id    INTEGER,
      monitor_id  TEXT,
      observed_at TEXT,
      vehicles    INTEGER,
      speed       REAL,
      occupancy   REAL,
      PRIMARY KEY (metro_id, monitor_id, observed_at)
    )
"""
)
conn.execute(
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_traffic_metro_monitor_observed
    ON traffic (metro_id, monitor_id, observed_at)
"""
)

# Capture count before insert so we can report new rows appended this run.
before_count = conn.execute(
    "SELECT COUNT(*) FROM traffic WHERE metro_id = ?",
    (BRUSSELS_METRO_ID,),
).fetchone()[0]

# Insert rows and ignore duplicates so repeated cron runs stay idempotent.
conn.executemany(
    """
    INSERT INTO traffic (metro_id, monitor_id, observed_at, vehicles, speed, occupancy)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(metro_id, monitor_id, observed_at) DO NOTHING
""",
    rows,
)
conn.commit()

# Count rows after insert and calculate net-new inserts for this run.
total_rows = conn.execute(
    "SELECT COUNT(*) FROM traffic WHERE metro_id = ?",
    (BRUSSELS_METRO_ID,),
).fetchone()[0]
inserted_rows = max(int(total_rows) - int(before_count), 0)
conn.close()


# 5. VERIFY ###################################

print(f"   candidate rows this run: {len(rows)}")
print(f"   new rows appended: {inserted_rows}")
print(f"   total rows (metro): {int(total_rows)}")
