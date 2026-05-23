# demo_data.py
# Static demo fixtures for Smart Charge (Tesla Model 3 showcase on launch).

from datetime import datetime, timedelta, timezone
from typing import Any

from utils import (
    utc_now_iso8601_halfhour,
    _parse_iso8601_utc,
    _slot_intensity_index,
)

DEMO_MAKE = "Tesla"
DEMO_MODEL = "Model 3"
DEFAULT_DEMO_CHARGING_HOURS = 4.0


def get_demo_ev_result() -> dict[str, Any]:
    """Tesla Model 3 specs (public reference values). Same shape as fetch_ev_from_api."""
    return {
        "success": True,
        "source": "demo",
        "data": [
            {
                "make": DEMO_MAKE,
                "model": DEMO_MODEL,
                "battery_capacity": "75 kWh",
                "battery_useable_capacity": "75 kWh",
                "charge_power": "11 kW AC",
            }
        ],
        "error_message": None,
    }


def get_demo_intensity_data() -> list[dict[str, Any]]:
    """
    Static 48h carbon intensity strip (~96 rows) anchored to current UTC half-hour.
    No network calls.
    """
    from_ts = utc_now_iso8601_halfhour()
    start = _parse_iso8601_utc(from_ts)
    if start is None:
        start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    # Believable daily pattern: greener overnight, higher during peak hours
    pattern = [
        "low",
        "low",
        "low",
        "moderate",
        "high",
        "high",
        "high",
        "moderate",
        "moderate",
        "low",
        "low",
        "low",
    ]
    forecasts = {"low": 118, "moderate": 215, "high": 335}
    rows = []
    for i in range(96):
        period_start = start + timedelta(minutes=30 * i)
        period_end = period_start + timedelta(minutes=30)
        idx = pattern[i % len(pattern)]
        rows.append({
            "from": period_start.strftime("%Y-%m-%dT%H:%MZ"),
            "to": period_end.strftime("%Y-%m-%dT%H:%MZ"),
            "forecast": forecasts.get(idx, 200),
            "index": idx,
        })
    return rows


def _periods_for_hours(hours: float) -> int:
    return max(1, int(round(hours / 0.5)))


def _index_score(index: str) -> int:
    idx = (index or "moderate").strip().lower()
    return {"low": 3, "moderate": 1, "high": 0}.get(idx, 1)


def _build_slots_from_intensity(
    intensity_data: list[dict], charging_hours: float
) -> list[dict[str, Any]]:
    """Pick up to 3 non-overlapping windows from static intensity (no LLM)."""
    rows = intensity_data[:96]
    n_periods = _periods_for_hours(charging_hours)
    if len(rows) < n_periods:
        return []

    candidates: list[tuple[int, int, str, str]] = []
    for i in range(len(rows) - n_periods + 1):
        window = rows[i : i + n_periods]
        score = sum(_index_score(r.get("index", "")) for r in window)
        start_iso = str(window[0].get("from") or "")
        end_iso = str(window[-1].get("to") or "")
        if start_iso and end_iso:
            candidates.append((score, i, start_iso, end_iso))

    candidates.sort(key=lambda x: (-x[0], x[1]))
    slots: list[dict[str, Any]] = []
    used_ranges: list[tuple[int, int]] = []

    for score, start_idx, start_iso, end_iso in candidates:
        end_idx = start_idx + n_periods - 1
        overlaps = any(not (end_idx < u0 or start_idx > u1) for u0, u1 in used_ranges)
        if overlaps:
            continue
        used_ranges.append((start_idx, end_idx))
        slot = {
            "start": start_iso,
            "end": end_iso,
            "reason": (
                "Illustrative window with sustained low carbon intensity."
                if score >= n_periods * 2
                else "Illustrative window with relatively lower carbon intensity."
            ),
        }
        slot["intensity_index"] = _slot_intensity_index(slot, intensity_data)
        slots.append(slot)
        if len(slots) >= 3:
            break

    return slots


def get_demo_slots_result(
    charging_hours: float = DEFAULT_DEMO_CHARGING_HOURS,
) -> dict[str, Any]:
    """Static slot recommendations aligned to demo intensity for chart highlight."""
    intensity_data = get_demo_intensity_data()
    slots = _build_slots_from_intensity(intensity_data, charging_hours)
    if not slots and len(intensity_data) >= 8:
        slots = [
            {
                "start": intensity_data[0]["from"],
                "end": intensity_data[7]["to"],
                "reason": "Illustrative overnight charging window.",
                "intensity_index": "low",
            }
        ]
    return {
        "success": True,
        "slots": slots,
        "error_message": None,
        "source": "demo",
    }
