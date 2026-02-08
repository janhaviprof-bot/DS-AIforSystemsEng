# utils.py
# API helpers for UK Carbon Intensity time series.
# Pairs with LAB_cursor_shiny_app.md
# Tim Fraser

# Helper functions for fetching and parsing UK Carbon Intensity API data.
# Handles errors and returns structured results for the Shiny app.

import re
import requests
import pandas as pd
from typing import Any


# Base URL for UK Carbon Intensity API (no API key required).
API_BASE = "https://api.carbonintensity.org.uk"


def validate_iso8601(value: str) -> bool:
    """
    Check that a string looks like ISO8601 datetime YYYY-MM-DDThh:mmZ.
    Used to validate user input before calling the API.
    """
    if not value or not value.strip():
        return False
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$"
    return bool(re.match(pattern, value.strip()))


def fetch_intensity(from_ts: str, to_ts: str) -> dict[str, Any]:
    """
    Fetch carbon intensity time series from the API.
    Returns a dict with keys: success, data, error_message.
    - success: True if request succeeded and we have data.
    - data: pandas DataFrame of intensity data, or None.
    - error_message: user-friendly error string, or None.
    """
    result = {"success": False, "data": None, "error_message": None}

    if not validate_iso8601(from_ts):
        result["error_message"] = (
            "Invalid start time. Use ISO8601 format: YYYY-MM-DDThh:mmZ "
            "(e.g. 2017-09-18T11:30Z)."
        )
        return result

    if not validate_iso8601(to_ts):
        result["error_message"] = (
            "Invalid end time. Use ISO8601 format: YYYY-MM-DDThh:mmZ "
            "(e.g. 2017-09-20T12:00Z)."
        )
        return result

    url = f"{API_BASE}/intensity/{from_ts}/{to_ts}"

    try:
        response = requests.get(url, timeout=15)
    except requests.exceptions.Timeout:
        result["error_message"] = "Request timed out. Please try again."
        return result
    except requests.exceptions.RequestException as e:
        result["error_message"] = f"Network error: {str(e)}"
        return result

    if response.status_code == 400:
        result["error_message"] = (
            "Bad request: use valid start and end datetimes in ISO8601 format "
            "YYYY-MM-DDThh:mmZ (e.g. /intensity/2017-08-25T15:30Z/2017-08-27T17:00Z)."
        )
        return result

    if response.status_code >= 500:
        result["error_message"] = "Server error. Please try again later."
        return result

    if response.status_code != 200:
        result["error_message"] = f"Unexpected response: {response.status_code}"
        return result

    try:
        body = response.json()
    except ValueError:
        result["error_message"] = "Invalid JSON in API response."
        return result

    data_list = body.get("data")
    if not data_list or not isinstance(data_list, list):
        result["error_message"] = "No time series data in response."
        return result

    # Flatten each item into a row for display.
    rows = []
    for item in data_list:
        from_val = item.get("from", "")
        to_val = item.get("to", "")
        intensity = item.get("intensity") or {}
        rows.append({
            "from": from_val,
            "to": to_val,
            "forecast": intensity.get("forecast"),
            "actual": intensity.get("actual"),
            "index": intensity.get("index", ""),
        })

    result["data"] = pd.DataFrame(rows)
    result["success"] = True
    return result


def fetch_generation(from_ts: str, to_ts: str) -> dict[str, Any]:
    """
    Fetch generation mix (power by source) from the API.
    Returns a dict with keys: success, data, error_message.
    - success: True if request succeeded and we have data.
    - data: pandas DataFrame with columns from, to, and one column per fuel (perc).
    - error_message: user-friendly error string, or None.
    """
    result = {"success": False, "data": None, "error_message": None}

    if not validate_iso8601(from_ts):
        result["error_message"] = (
            "Invalid start time. Use ISO8601 format: YYYY-MM-DDThh:mmZ."
        )
        return result

    if not validate_iso8601(to_ts):
        result["error_message"] = (
            "Invalid end time. Use ISO8601 format: YYYY-MM-DDThh:mmZ."
        )
        return result

    url = f"{API_BASE}/generation/{from_ts}/{to_ts}"

    try:
        response = requests.get(url, timeout=15)
    except requests.exceptions.Timeout:
        result["error_message"] = "Request timed out. Please try again."
        return result
    except requests.exceptions.RequestException as e:
        result["error_message"] = f"Network error: {str(e)}"
        return result

    if response.status_code == 400:
        result["error_message"] = (
            "Bad request: use valid start and end datetimes in ISO8601 format."
        )
        return result

    if response.status_code >= 500:
        result["error_message"] = "Server error. Please try again later."
        return result

    if response.status_code != 200:
        result["error_message"] = f"Unexpected response: {response.status_code}"
        return result

    try:
        body = response.json()
    except ValueError:
        result["error_message"] = "Invalid JSON in API response."
        return result

    data_list = body.get("data")
    if not data_list or not isinstance(data_list, list):
        result["error_message"] = "No generation mix data in response."
        return result

    # Flatten: one row per period; generationmix becomes columns (fuel -> perc).
    rows = []
    for item in data_list:
        from_val = item.get("from", "")
        to_val = item.get("to", "")
        row = {"from": from_val, "to": to_val}
        for entry in item.get("generationmix") or []:
            fuel = entry.get("fuel", "")
            perc = entry.get("perc")
            if fuel:
                row[fuel] = perc
        rows.append(row)

    result["data"] = pd.DataFrame(rows)
    result["success"] = True
    return result
