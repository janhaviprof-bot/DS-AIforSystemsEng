"""
lab_agents.py
Weather-aware multi-agent travel itinerary
Pairs with 03_agents.py and 04_rules.py
"""

# 0. SETUP ###################################

import os
from pathlib import Path
import json
import re

import requests  # HTTP APIs
import yaml      # rules

from functions import agent_run


# Set working directory to this script's folder.
os.chdir(Path(__file__).resolve().parent)

# Load OPENTRIPMAP_API_KEY from project root .env (dsai/.env), if present.
root_env_path = Path(__file__).resolve().parent.parent / ".env"
if root_env_path.exists():
    with open(root_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("OPENTRIPMAP_API_KEY="):
                _, value = line.split("=", 1)
                os.environ["OPENTRIPMAP_API_KEY"] = value.strip()
                break


# 1. API HELPERS ###################################

def _get_opentripmap_api_key() -> str:
    key = os.getenv("OPENTRIPMAP_API_KEY")
    if not key:
        raise RuntimeError("OPENTRIPMAP_API_KEY is not set in the environment.")
    return key


def get_city_attractions(city: str, limit: int = 7) -> dict:
    """Return a small set of attractions for the city using OpenTripMap."""
    api_key = _get_opentripmap_api_key()

    # Geocode city
    geo_resp = requests.get(
        "https://api.opentripmap.com/0.1/en/places/geoname",
        params={"name": city, "apikey": api_key},
        headers={"Accept": "application/json"},
    )
    geo_resp.raise_for_status()
    geo = geo_resp.json()
    lat, lon = geo.get("lat"), geo.get("lon")
    if lat is None or lon is None:
        return {"city": city, "attractions": []}

    # Nearby points of interest and food
    poi_resp = requests.get(
        "https://api.opentripmap.com/0.1/en/places/radius",
        params={
            "radius": 5000,
            "lon": lon,
            "lat": lat,
            "kinds": "interesting_places,foods,cafes,restaurants,bars",
            "limit": limit,
            "apikey": api_key,
        },
        headers={"Accept": "application/json"},
    )
    poi_resp.raise_for_status()
    features = poi_resp.json().get("features", [])

    attractions = []
    indoor_kinds = {"museum", "theatre", "theater", "gallery", "shopping_mall"}
    outdoor_kinds = {"park", "garden", "playground", "beach", "forest"}

    for item in features:
        props = item.get("properties", {})
        name = (props.get("name") or "").strip()
        if not name:
            continue
        kinds = (props.get("kinds") or "").split(",")
        category = kinds[0] if kinds else "attraction"
        k_lower = category.lower()
        indoor = k_lower in indoor_kinds or (k_lower not in outdoor_kinds)
        attractions.append(
            {
                "name": name,
                "category": category,
                "indoor": indoor,
                "short_description": f"{category.capitalize()} in {city} suitable for visitors.",
            }
        )

    return {"city": city, "attractions": attractions}


def get_city_weather(city: str) -> dict:
    """Return a simple weather summary for a city using Open-Meteo."""
    # Geocode
    g_resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1},
        headers={"Accept": "application/json"},
    )
    g_resp.raise_for_status()
    gdata = g_resp.json()
    results = gdata.get("results") or []
    if not results:
        return {
            "city": city,
            "date": "",
            "summary": "Weather data unavailable.",
            "morning": {"temp_c": 0, "conditions": "unknown", "precipitation": "low"},
            "afternoon": {"temp_c": 0, "conditions": "unknown", "precipitation": "low"},
            "evening": {"temp_c": 0, "conditions": "unknown", "precipitation": "low"},
        }

    lat, lon = results[0]["latitude"], results[0]["longitude"]

    # Forecast
    f_resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,precipitation",
            "timezone": "auto",
        },
        headers={"Accept": "application/json"},
    )
    f_resp.raise_for_status()
    hourly = f_resp.json().get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    precs = hourly.get("precipitation", [])

    if not times or not temps or not precs:
        return {
            "city": city,
            "date": "",
            "summary": "Weather data unavailable.",
            "morning": {"temp_c": 0, "conditions": "unknown", "precipitation": "low"},
            "afternoon": {"temp_c": 0, "conditions": "unknown", "precipitation": "low"},
            "evening": {"temp_c": 0, "conditions": "unknown", "precipitation": "low"},
        }

    first_date = times[0].split("T")[0]

    def block(start_hour: int, end_hour: int) -> dict:
        t_vals, p_vals = [], []
        for t_str, temp, prec in zip(times, temps, precs):
            date_part, hour_part = t_str.split("T")
            if date_part != first_date:
                continue
            hour = int(hour_part.split(":")[0])
            if start_hour <= hour < end_hour:
                t_vals.append(temp)
                p_vals.append(prec)
        avg_t = sum(t_vals) / len(t_vals) if t_vals else 0.0
        avg_p = sum(p_vals) / len(p_vals) if p_vals else 0.0
        if avg_p < 0.2:
            precip = "low"
            cond = "clear" if avg_t >= 5 else "cloudy"
        elif avg_p < 1.0:
            precip, cond = "medium", "light rain"
        else:
            precip, cond = "high", "rain"
        return {"temp_c": round(avg_t, 1), "conditions": cond, "precipitation": precip}

    morning = block(6, 12)
    afternoon = block(12, 18)
    evening = block(18, 24)
    summary = (
        f"Morning around {morning['temp_c']}°C with {morning['conditions']}, "
        f"afternoon near {afternoon['temp_c']}°C with {afternoon['conditions']}, "
        f"and evening close to {evening['temp_c']}°C with {evening['conditions']}."
    )

    return {
        "city": city,
        "date": first_date,
        "summary": summary,
        "morning": morning,
        "afternoon": afternoon,
        "evening": evening,
    }


LAB_RULES_FILE = "lab_rules.yaml"


def _load_rules() -> dict:
    with open(LAB_RULES_FILE, "r") as f:
        return yaml.safe_load(f)["rules"]


def _rules_text(ruleset: dict) -> str:
    return f"{ruleset['name']}\n{ruleset['description']}\n\n{ruleset['guidance']}"


def format_weather_as_table(weather: dict) -> str:
    """Create a small markdown table from the weather summary."""
    if not weather:
        return "No weather data available."

    rows = []
    for label in ["morning", "afternoon", "evening"]:
        block = weather.get(label, {})
        rows.append(
            {
                "Period": label.title(),
                "Temp (°C)": block.get("temp_c", ""),
                "Conditions": block.get("conditions", ""),
                "Precip": block.get("precipitation", ""),
            }
        )

    header = "| Period | Temp (°C) | Conditions | Precip |\n|--------|-----------|------------|--------|"
    body = [
        f"| {r['Period']} | {r['Temp (°C)']} | {r['Conditions']} | {r['Precip']} |"
        for r in rows
    ]
    return "\n".join([header] + body)


# 2. CONFIGURATION & PROMPTS ###################################

MODEL = "smollm2:1.7b"

_rules = _load_rules()
rules_attractions = _rules["collector"][0]
rules_weather = _rules["weather"][0]
rules_itinerary = _rules["itinerary"][0]
rules_schedule = _rules["schedule"][0]

# Agent 1 – Attractions
role_attractions = (
    "You are a travel attractions agent. "
    "The user gives you raw JSON from an attractions HTTP API for a single city. "
    "Read it and return a concise **markdown table** of the most popular and most interesting "
    "attractions that reflect the city's culture and history.\n\n"
    f"{_rules_text(rules_attractions)}"
)

# Agent 2 – Weather
role_weather_agent = (
    "You are a travel weather agent. "
    "The user gives you raw JSON from a weather HTTP API for one city and one day. "
    "Summarize the weather into morning, afternoon, and evening JSON blocks."
    "Explicitly state major weather highlighths to be aware about\n\n"
    f"{_rules_text(rules_weather)}"
)

# Agent 3 – Weather-aware Itinerary
role_itinerary = (
    "You are a helpful, weather-aware travel planner. "
    "The user gives you JSON with a city, an attractions list, and a weather summary. "
    "Design a realistic one-day plan using only the listed attractions. "
    "Make sure to make the plan sensitive to weather to enhance the user experience.\n\n"
    f"{_rules_text(rules_itinerary)}"
)

# Agent 4 – Timed To-Do Scheduler
role_schedule = ("""
You are a precise travel day scheduler. Your job is to convert a city itinerary 
into a realistic, time-stamped to-do list for a single day.

You will receive a JSON object with:
- "city": the destination city
- "itinerary_markdown": a one-day plan with activities and recommendations
- "known_places": list of attractions with names and categories
- "meal_places": list of food/cafe/restaurant options from the attractions

## OUTPUT FORMAT
Return ONLY a time-stamped to-do list in this exact format — no extra commentary, 
no markdown headers, just the list:

08:00 - 08:45 | Breakfast at [place name] — [one sentence why or what to order]
09:00 - 10:30 | Visit [attraction name] — [one sentence what to do or see there]
10:45 - 12:00 | Explore [place/area] — [one sentence tip]
12:00 - 13:00 | Lunch at [place name] — [one sentence recommendation]
...and so on until evening.

## STRICT RULES
1. Every activity MUST have a start time and end time (e.g. 09:00 - 10:30).
2. Start the day at 08:00 and end by 21:00 or 22:00.
3. Include breakfast, lunch, and dinner using the meal_places provided. 
   If no meal place fits, suggest a generic local option by neighborhood.
4. Leave 15-minute travel buffers between back-to-back locations.
5. Do NOT drop any activity from the itinerary_markdown — every attraction must appear.
6. If the weather is bad (rain, cold), move outdoor activities to mid-day 
   when conditions are best, and schedule indoor activities in the morning/evening.
7. Keep each description to one sentence — specific and useful, not generic filler.
8. Do not add any intro sentence, title, or closing remark — output the list only.
""")


# 3. SCHEDULER HELPER ###################################

def run_scheduler_with_validation(
    city: str,
    itinerary_markdown: str,
    attractions_api_data: dict,
    meal_places: list[dict],
    model: str,
) -> str:
    """Run the scheduler agent once and return whatever timed list it produces."""
    payload = {
        "city": city,
        "itinerary_markdown": itinerary_markdown,
        "known_places": attractions_api_data.get("attractions", []),
        "meal_places": meal_places,
    }
    return agent_run(
        role=role_schedule,
        task=json.dumps(payload, indent=2),
        model=model,
        output="text",
    )


# 4. WORKFLOW FUNCTION ###################################

def run_travel_itinerary_workflow(city: str, model: str = MODEL) -> dict:
    """Four-agent travel itinerary workflow, similar style to 03_agents.py."""

    # Task 1 - Functions: fetch attractions and weather
    attractions_api_data = get_city_attractions(city=city, limit=7)
    weather_api_data = get_city_weather(city=city)

    # Task 2 - Attractions Agent
    attractions_output = agent_run(
        role=role_attractions,
        task=json.dumps(attractions_api_data, indent=2),
        model=model,
        output="text",
    )

    # Task 3 - Weather Agent
    weather_output = agent_run(
        role=role_weather_agent,
        task=json.dumps(weather_api_data, indent=2),
        model=model,
        output="text",
    )

    # Task 4 - Itinerary Agent
    try:
        attractions_parsed = json.loads(attractions_output)
    except json.JSONDecodeError:
        attractions_parsed = attractions_api_data
    try:
        weather_parsed = json.loads(weather_output)
    except json.JSONDecodeError:
        weather_parsed = weather_api_data

    itinerary_input = json.dumps(
        {
            "city": city,
            "attractions": attractions_parsed.get("attractions", []),
            "weather": weather_parsed,
        },
        indent=2,
    )
    itinerary_output = agent_run(
        role=role_itinerary,
        task=itinerary_input,
        model=model,
        output="text",
    )

    # Task 5 - Scheduler Agent
    meal_places = [
        p
        for p in attractions_api_data.get("attractions", [])
        if any(k in str(p.get("category", "")).lower() for k in ["food", "foods", "cafe", "cafes", "restaurant", "restaurants", "bar", "bars"])
    ]
    schedule_output = run_scheduler_with_validation(
        city=city,
        itinerary_markdown=itinerary_output,
        attractions_api_data=attractions_api_data,
        meal_places=meal_places,
        model=model,
    )

    return {
        "attractions_api_data": attractions_api_data,
        "weather_api_data": weather_api_data,
        "attractions_output": attractions_output,
        "itinerary_output": itinerary_output,
        "schedule_output": schedule_output,
    }


# 5. DEMO RUN ###################################

if __name__ == "__main__":
    # Simple demo for one city (students can change the city name)
    example_city = "Boston"
    print(f"Running weather-aware travel itinerary workflow for: {example_city}")

    results = run_travel_itinerary_workflow(city=example_city, model=MODEL)

    # Show a tiny API sample so students see raw data structure
    api_sample = results["attractions_api_data"]["attractions"][:2]
    print("\n=== Sample Attractions from API ===")
    print(json.dumps(api_sample, indent=2))

    # Show intermediate agent outputs (for learning the multi-agent flow)
    print("\n=== Agent 1: Attractions Agent (JSON) ===")
    print(results["attractions_output"])

    print("\n=== Agent 2: Weather Agent (JSON) ===")
    weather_src = results.get("weather_output", results["weather_api_data"])
    print(weather_src)
    print("\n=== Agent 2: Weather Agent (Table) ===")
    # Use parsed JSON if the agent returned JSON; otherwise fall back to API data.
    try:
        weather_for_table = json.loads(weather_src) if isinstance(weather_src, str) else weather_src
    except json.JSONDecodeError:
        weather_for_table = results["weather_api_data"]
    print(format_weather_as_table(weather_for_table))

    # Show final itinerary and timed to-do list
    print("\n=== Final Itinerary (Agent 3) ===")
    print(results["itinerary_output"])

    print("\n=== Timed To-Do List (Agent 4) ===")
    print(results["schedule_output"])

