# utils.py
# API and Ollama helpers for EV Charger app.
# Tim Fraser

# Helper functions: (1) Ollama Cloud to extract make/model from user text,
# (2) API Ninjas to fetch EV data by make/model. Returns structured
# results for the Shiny app. Load from root .env: OLLAMA_API_KEY, EV_API_KEY.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import os
import re
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# Load .env from project root or from charger_app directory
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv(Path(__file__).resolve().parent / ".env")

# 1. OLLAMA CLOUD – EXTRACT MAKE AND MODEL #################################

OLLAMA_CLOUD_URL = "https://ollama.com/api/chat"

MAKE_MODEL_PROMPT = """You are a car expert. The user described an electric vehicle. Extract only the manufacturer (make) and model name.

User input: "{user_input}"

Respond with exactly a JSON object, nothing else, in this format:
{{"make": "ManufacturerName", "model": "ModelName"}}

Use proper capitalization (e.g. Tesla, Model 3). If you cannot determine make or model, use empty string for that field. Output only the JSON object."""


def _call_ollama_cloud(prompt: str) -> dict[str, Any]:
    """
    Call Ollama Cloud /api/chat. Requires OLLAMA_API_KEY. Returns raw response dict or error.
    """
    api_key = os.getenv("OLLAMA_API_KEY")
    if not api_key or not api_key.strip():
        return {"error": "OLLAMA_API_KEY not set in .env"}
    body = {
        "model": "gpt-oss:20b-cloud",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        # Use 120s timeout; slot suggestions send a large prompt and can take a while
        response = requests.post(OLLAMA_CLOUD_URL, headers=headers, json=body, timeout=120)
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Ollama Cloud is slow or unreachable; try again in a moment."}
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {str(e)}"}
    if response.status_code != 200:
        return {"error": f"Ollama Cloud returned {response.status_code}"}
    try:
        return response.json()
    except ValueError:
        return {"error": "Invalid JSON from Ollama Cloud"}


def _parse_make_model_from_text(text: str) -> tuple[str, str]:
    """
    Try to extract make and model from LLM response text (e.g. JSON or "Make: X, Model: Y").
    Returns (make, model); empty strings if not found.
    """
    make = ""
    model = ""
    text = (text or "").strip()
    # Try JSON: {"make": "X", "model": "Y"}
    json_match = re.search(r'\{[^{}]*"make"[^{}]*"model"[^{}]*\}', text, re.DOTALL | re.IGNORECASE)
    if json_match:
        try:
            obj = json.loads(json_match.group(0))
            make = str(obj.get("make", "")).strip()
            model = str(obj.get("model", "")).strip()
            return (make, model)
        except (json.JSONDecodeError, TypeError):
            pass
    # Fallback: "Make: X" / "Model: Y"
    make_m = re.search(r'"make"\s*:\s*"([^"]*)"', text, re.IGNORECASE)
    model_m = re.search(r'"model"\s*:\s*"([^"]*)"', text, re.IGNORECASE)
    if make_m:
        make = make_m.group(1).strip()
    if model_m:
        model = model_m.group(1).strip()
    return (make, model)


def parse_make_model_with_ollama(user_input: str) -> dict[str, Any]:
    """
    Use Ollama Cloud to extract make and model from free-text user input.
    Returns dict with success, make, model, or error_message.
    """
    result = {"success": False, "make": "", "model": "", "error_message": None}
    prompt = MAKE_MODEL_PROMPT.format(user_input=user_input or "")
    raw = _call_ollama_cloud(prompt)
    if "error" in raw:
        result["error_message"] = raw["error"]
        return result
    text = ""
    if "message" in raw and isinstance(raw["message"], dict):
        text = raw["message"].get("content") or ""
    make, model = _parse_make_model_from_text(text)
    result["make"] = make
    result["model"] = model
    result["success"] = True
    return result


# 2. API NINJAS – EV DATA #################################

EV_API_BASE = "https://api.api-ninjas.com/v1/electricvehicle"


def fetch_ev_from_api(make: str, model: str) -> dict[str, Any]:
    """
    Fetch electric vehicle data from API Ninjas. Requires EV_API_KEY in root .env.
    Returns dict with success, data (list of vehicle dicts), error_message.
    """
    result = {"success": False, "data": None, "error_message": None}
    api_key = os.getenv("EV_API_KEY")
    if not api_key or not api_key.strip():
        result["error_message"] = "EV_API_KEY not set in .env."
        return result
    make = (make or "").strip()
    model = (model or "").strip()
    if not make or not model:
        result["error_message"] = "Make and model are required."
        return result
    params = {"make": make, "model": model}
    headers = {"X-Api-Key": api_key.strip()}
    try:
        response = requests.get(EV_API_BASE, params=params, headers=headers, timeout=15)
    except requests.exceptions.Timeout:
        result["error_message"] = "EV API request timed out."
        return result
    except requests.exceptions.RequestException as e:
        result["error_message"] = f"Network error: {str(e)}"
        return result
    if response.status_code != 200:
        result["error_message"] = f"API returned {response.status_code}. Try checking make/model spelling."
        return result
    try:
        data_list = response.json()
    except ValueError:
        result["error_message"] = "Invalid JSON from API."
        return result
    if not isinstance(data_list, list):
        result["error_message"] = "Unexpected API response format."
        return result
    if not data_list:
        result["error_message"] = "No vehicle found for that make and model. Check spelling or try a different name."
        return result
    result["data"] = data_list
    result["success"] = True
    result["source"] = "api"
    return result


# 3. LLM FALLBACK – EV SPECS #################################

EV_LLM_PROMPT = """You are an expert on electric vehicles. Given make and model, provide approximate specs in JSON only.

Make: {make}
Model: {model}

Return exactly one JSON object with these keys (use empty string if unknown):
{{"make": "MakeName", "model": "ModelName", "battery_capacity": "XX kWh", "charge_power": "XX kW AC"}}
Output only the JSON object."""


def _parse_ev_from_llama_response(text: str) -> dict[str, Any] | None:
    """Extract a single vehicle dict from LLM response."""
    text = (text or "").strip()
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    out = json.loads(text[start : i + 1])
                    if isinstance(out, dict):
                        return out
                except (json.JSONDecodeError, TypeError):
                    pass
                return None
    return None


def fetch_ev_from_llama(make: str, model: str) -> dict[str, Any]:
    """
    Fallback: ask LLM for approximate EV specs when API returns nothing.
    Returns same shape as fetch_ev_from_api: success, data (list of one vehicle dict), error_message, source="llm".
    """
    result = {"success": False, "data": None, "error_message": None, "source": "llm"}
    make = (make or "").strip()
    model = (model or "").strip()
    if not make or not model:
        result["error_message"] = "Make and model are required."
        return result
    prompt = EV_LLM_PROMPT.format(make=make, model=model)
    raw = _call_ollama_cloud(prompt)
    if "error" in raw:
        result["error_message"] = raw["error"]
        return result
    text = ""
    if "message" in raw and isinstance(raw["message"], dict):
        text = raw["message"].get("content") or ""
    vehicle = _parse_ev_from_llama_response(text)
    if not vehicle:
        result["error_message"] = "Could not parse EV specs from LLM response."
        return result
    # Normalize keys to match API shape (battery_capacity, battery_useable_capacity, charge_power)
    normalized = {
        "make": vehicle.get("make", make),
        "model": vehicle.get("model", model),
        "battery_capacity": vehicle.get("battery_capacity", ""),
        "battery_useable_capacity": vehicle.get("battery_useable_capacity") or vehicle.get("battery_usable_capacity", ""),
        "charge_power": vehicle.get("charge_power", ""),
    }
    result["data"] = [normalized]
    result["success"] = True
    return result


# 4. CHARGING TIME #################################

def _parse_kwh(s: str) -> float | None:
    """Parse a string like '50 kWh' or '50' to float kWh."""
    if s is None or str(s).strip() == "":
        return None
    s = str(s).strip()
    m = re.search(r"([\d.]+)\s*kWh?", s, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    try:
        return float(re.sub(r"[^\d.]", "", s) or 0)
    except ValueError:
        return None


def _parse_kw(s: str) -> float | None:
    """Parse a string like '11 kW' or '11' to float kW."""
    if s is None or str(s).strip() == "":
        return None
    s = str(s).strip()
    m = re.search(r"([\d.]+)\s*kW?", s, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    try:
        return float(re.sub(r"[^\d.]", "", s) or 0)
    except ValueError:
        return None


def charging_time_hours(battery_capacity_str: str, charge_power_str: str) -> float | None:
    """
    Compute charging time in hours: battery_capacity (kWh) / charge_power (kW).
    Returns None if either value cannot be parsed or charge_power is zero.
    """
    kwh = _parse_kwh(battery_capacity_str)
    kw = _parse_kw(charge_power_str)
    if kwh is None or kw is None or kw <= 0:
        return None
    return round(kwh / kw, 2)


# 5. UK CARBON INTENSITY – 48H AND CHARGING SLOTS #################################

CARBON_INTENSITY_BASE = "https://api.carbonintensity.org.uk"
UK_TZ = ZoneInfo("Europe/London")


def utc_now_iso8601_halfhour() -> str:
    """
    Return current UTC time rounded to the current or next half-hour in ISO8601 format
    (YYYY-MM-DDThh:mmZ) for the Carbon Intensity API.
    """
    now = datetime.now(timezone.utc)
    minute = 30 if now.minute >= 30 else 0
    rounded = now.replace(minute=minute, second=0, microsecond=0)
    return rounded.strftime("%Y-%m-%dT%H:%MZ")


def format_utc_to_uk_display(utc_str: str) -> str:
    """
    Convert a UTC datetime string (ISO8601) to UK local time and return a display string
    with GMT or BST based on season (e.g. "14:00 GMT" or "15:00 BST").
    """
    if not utc_str or not str(utc_str).strip():
        return ""
    try:
        s = str(utc_str).strip().replace("Z", "+00:00")
        if "+00:00" not in s and s[-1] != "Z":
            s = s + "Z"
        dt_utc = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        dt_uk = dt_utc.astimezone(UK_TZ)
        label = "BST" if dt_uk.dst() else "GMT"
        return dt_uk.strftime("%H:%M") + " " + label
    except (ValueError, TypeError):
        return str(utc_str)


def format_utc_to_uk_display_with_date(
    utc_str: str, ref_utc_now: datetime | None = None
) -> str:
    """
    Convert a UTC datetime string to UK local time and return a display string with
    date, time and GMT/BST. E.g. "13 Feb 14:00 GMT", "14 Feb 02:00 GMT", "15 Feb 08:00 BST".
    """
    if not utc_str or not str(utc_str).strip():
        return ""
    try:
        s = str(utc_str).strip().replace("Z", "+00:00")
        if "+00:00" not in s and s[-1] != "Z":
            s = s + "Z"
        dt_utc = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        dt_uk = dt_utc.astimezone(UK_TZ)
        label = "BST" if dt_uk.dst() else "GMT"
        date_part = dt_uk.strftime("%d %b")
        time_part = dt_uk.strftime("%H:%M") + " " + label
        return f"{date_part} {time_part}"
    except (ValueError, TypeError):
        return str(utc_str)


def fetch_intensity_48h(from_ts: str) -> dict[str, Any]:
    """
    Fetch UK Carbon Intensity for 48 hours from the given UTC datetime.
    GET /intensity/{from}/fw48h. No API key. Returns { success, data, error_message }.
    data is a list of dicts with from, to, forecast, index.
    """
    result = {"success": False, "data": None, "error_message": None}
    if not from_ts or not str(from_ts).strip():
        result["error_message"] = "Missing start time for 48h request."
        return result
    from_ts = str(from_ts).strip()
    url = f"{CARBON_INTENSITY_BASE}/intensity/{from_ts}/fw48h"
    try:
        response = requests.get(url, timeout=15)
    except requests.exceptions.Timeout:
        result["error_message"] = "Carbon Intensity request timed out. Please try again."
        return result
    except requests.exceptions.RequestException as e:
        result["error_message"] = f"Network error: {str(e)}"
        return result
    if response.status_code >= 500:
        result["error_message"] = "Carbon Intensity server error. Please try again later."
        return result
    if response.status_code != 200:
        result["error_message"] = f"Carbon Intensity API returned {response.status_code}."
        return result
    try:
        body = response.json()
    except ValueError:
        result["error_message"] = "Invalid JSON from Carbon Intensity API."
        return result
    data_list = body.get("data")
    if not data_list or not isinstance(data_list, list):
        result["error_message"] = "No intensity data in response."
        return result
    rows = []
    for item in data_list:
        from_val = item.get("from", "")
        to_val = item.get("to", "")
        intensity = item.get("intensity") or {}
        rows.append({
            "from": from_val,
            "to": to_val,
            "forecast": intensity.get("forecast"),
            "index": intensity.get("index", ""),
        })
    result["data"] = rows
    result["success"] = True
    return result


# 5. OPENAI – CHAT COMPLETIONS (BEST CHARGING SLOTS) #################################

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


def _call_openai_chat(prompt: str, model: str = "gpt-4o-mini") -> dict[str, Any]:
    """
    Call OpenAI Chat Completions API. Requires OPENAI_API_KEY.
    Returns {"message": {"content": text}} on success, {"error": "..."} on failure.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        return {"error": "OPENAI_API_KEY not set in .env"}
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False}
    try:
        response = requests.post(OPENAI_CHAT_URL, headers=headers, json=body, timeout=120)
    except requests.exceptions.Timeout:
        return {"error": "Request timed out."}
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {str(e)}"}
    if response.status_code != 200:
        return {"error": f"OpenAI API returned {response.status_code}"}
    try:
        data = response.json()
    except ValueError:
        return {"error": "Invalid JSON from OpenAI"}
    choices = data.get("choices") or []
    if not choices or not isinstance(choices, list):
        return {"error": "No choices in OpenAI response"}
    msg = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not msg or not isinstance(msg, dict):
        return {"error": "Invalid message in OpenAI response"}
    content = msg.get("content") or ""
    return {"message": {"content": content}}


SLOTS_PROMPT = """
You are an expert in UK carbon intensity forecasting and EV smart charging optimization.

TASK:
The user must charge their electric vehicle for {charging_hours} continuous hours.
You are given a 48-hour carbon intensity forecast where each row represents a 30-minute period.

Each row contains:
- start time (UTC)
- end time (UTC)
- forecast intensity (gCO2/kWh)
- intensity index (low/moderate/high)

DATA:
{intensity_summary}

GOAL:
Suggest 3 to 5 feasible charging time slots within the next 48 hours.

CONSTRAINTS:
1. Each slot must be at least {charging_hours} continuous hours long.
2. Slots must consist only of contiguous 30-minute periods from the dataset.
3. Prefer lowest carbon intensity periods first.
4. Avoid high intensity periods if low or moderate alternatives exist.
5. If multiple similar options exist, prefer:
   - lowest average carbon intensity
   - longer continuous low-intensity windows
   - earlier time slots (tie-breaker)
6. Never suggest overlapping slots.
7. Use ONLY data provided — do not invent forecast values.

EDGE CASES:
- If fewer than 3 valid low-intensity slots exist, include moderate ones.
- If still insufficient, include best available options ranked by lowest average intensity.
- If no valid slot meets {charging_hours}, return an empty JSON array [].

OUTPUT FORMAT (STRICT):
Return ONLY a JSON array. No explanation, no markdown, no extra text.

Each object must contain:
- "start": ISO8601 UTC start time
- "end": ISO8601 UTC end time
- "reason": short explanation (≤12 words)

Example:
[
  {{"start": "2025-02-13T02:00Z", "end": "2025-02-13T07:30Z", "reason": "Sustained low overnight intensity"}},
  {{"start": "2025-02-13T23:00Z", "end": "2025-02-14T04:00Z", "reason": "Lowest average carbon window"}}
]

Return only the JSON array.
"""


def _parse_iso8601_utc(s: str) -> datetime | None:
    """Parse ISO8601 UTC string to timezone-aware datetime. Returns None on failure."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip().replace("Z", "+00:00")
    if "+00:00" not in s and "-" not in s[10:]:
        s = s + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def iso8601_to_google_date(iso8601_str: str) -> str:
    """
    Convert ISO8601 UTC string to Google Calendar format YYYYMMDDTHHMMSSZ.
    Returns empty string on failure.
    """
    dt = _parse_iso8601_utc(iso8601_str or "")
    if dt is None:
        return ""
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _slot_intensity_index(slot: dict[str, Any], intensity_data: list[dict]) -> str:
    """
    Compute dominant intensity index (low/moderate/high) for a slot from overlapping
    30-minute intensity periods. Returns the most common index; ties use worst (high > moderate > low).
    """
    start_dt = _parse_iso8601_utc(slot.get("start") or "")
    end_dt = _parse_iso8601_utc(slot.get("end") or "")
    if start_dt is None or end_dt is None or end_dt <= start_dt:
        return "moderate"
    counts: dict[str, int] = {"low": 0, "moderate": 0, "high": 0}
    for row in intensity_data:
        row_from = _parse_iso8601_utc(str(row.get("from") or ""))
        row_to = _parse_iso8601_utc(str(row.get("to") or ""))
        if row_from is None or row_to is None:
            continue
        if start_dt >= row_to or end_dt <= row_from:
            continue
        idx = (row.get("index") or "").strip().lower()
        if idx in counts:
            counts[idx] += 1
    if sum(counts.values()) == 0:
        return "moderate"
    best = max(counts, key=lambda k: (counts[k], {"low": 0, "moderate": 1, "high": 2}[k]))
    return best


def _parse_slots_from_text(text: str) -> list[dict[str, Any]]:
    """Extract list of slot dicts (start, end, reason) from LLM response."""
    text = (text or "").strip()
    slots = []
    start_idx = text.find("[")
    if start_idx < 0:
        return slots
    depth = 0
    for i in range(start_idx, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                json_str = text[start_idx : i + 1]
                break
    else:
        return slots
    try:
        arr = json.loads(json_str)
        if not isinstance(arr, list):
            return slots
        for item in arr:
            if not isinstance(item, dict):
                continue
            start_val = item.get("start") or item.get("from")
            end_val = item.get("end") or item.get("to")
            reason = item.get("reason") or ""
            if start_val and end_val:
                slots.append({"start": str(start_val), "end": str(end_val), "reason": str(reason)})
    except (json.JSONDecodeError, TypeError):
        pass
    if not slots:
        for m in re.finditer(r'"start"\s*:\s*"([^"]+)"\s*,\s*"end"\s*:\s*"([^"]+)"\s*,\s*"reason"\s*:\s*"([^"]*)"', text):
            slots.append({"start": m.group(1), "end": m.group(2), "reason": m.group(3)})
    return slots


def suggest_charging_slots_llama(charging_hours: float, intensity_data: list[dict]) -> dict[str, Any]:
    """
    Ask OpenAI to suggest feasible charging slots from 48h intensity data.
    Returns { success, slots: list[dict], error_message }. Each slot has start, end, reason.
    """
    result = {"success": False, "slots": [], "error_message": None}
    if not intensity_data:
        result["error_message"] = "No intensity data to analyze."
        return result
    lines = []
    for i, row in enumerate(intensity_data[:96]):
        from_val = row.get("from", "")
        to_val = row.get("to", "")
        forecast = row.get("forecast", "")
        idx = row.get("index", "")
        lines.append(f"  {from_val} to {to_val}  forecast={forecast}  index={idx}")
    intensity_summary = "\n".join(lines)
    prompt = SLOTS_PROMPT.format(charging_hours=charging_hours, intensity_summary=intensity_summary)
    raw = _call_openai_chat(prompt)
    if "error" in raw:
        result["error_message"] = raw["error"]
        return result
    text = ""
    if "message" in raw and isinstance(raw["message"], dict):
        text = raw["message"].get("content") or ""
    slots = _parse_slots_from_text(text)
    if not slots:
        result["error_message"] = "Could not parse suggested slots from the response. Try again."
        return result
    for slot in slots:
        slot["intensity_index"] = _slot_intensity_index(slot, intensity_data)
    result["success"] = True
    result["slots"] = slots
    return result
