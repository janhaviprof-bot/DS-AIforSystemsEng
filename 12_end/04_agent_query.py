# 04_agent_query.py
# Agent with REST Tool Call
# Pairs with 04_agent_query.R
# Tim Fraser

import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "08_function_calling"))

from dotenv import load_dotenv
from functions import agent

import requests

# 1. CONFIG ###################################

load_dotenv(ROOT_DIR / "12_end" / ".env")

ENDPOINT_URL = os.getenv("API_PUBLIC_URL", "http://localhost:8000").rstrip("/")
MODEL = os.getenv("OLLAMA_MODEL", "smollm2:1.7b")

UNIT_NOTE = "vehicles observed in one representative minute (1m/t1 interval) within the requested hour and day of week"

# 2. DEFINE TOOL FUNCTION ###################################

def predict_vehicle_count(day_of_week, hours_of_day):
    hours = [int(h) for h in hours_of_day if 0 <= int(h) <= 23]
    if not hours:
        raise ValueError("hours_of_day must contain at least one integer between 0 and 23.")

    predictions = []
    for hour in hours:
        resp = requests.get(
            f"{ENDPOINT_URL}/predict",
            params={"day_of_week": int(day_of_week), "hour_of_day": hour},
            timeout=10,
        )
        resp.raise_for_status()
        predictions.append(
            {
                "hour_of_day": hour,
                "predicted_vehicle_count": float(resp.json()["predicted_vehicle_count"]),
            }
        )

    return {
        "day_of_week": int(day_of_week),
        "unit": "vehicles_observed_in_one_minute",
        "interval": "1m_t1",
        "note": "Each prediction is for one representative minute within that hour and day of week.",
        "predictions": predictions,
    }

# 3. DEFINE TOOL METADATA ###################################

tool_predict_vehicle_count = {
    "type": "function",
    "function": {
        "name": "predict_vehicle_count",
        "description": (
            "Predict Brussels vehicle count for a specific day of week and vector of hours. "
            "Returns one estimated vehicle count per requested hour. "
            "Each value is for one representative minute (1m/t1 interval) within that hour on that day of week."
        ),
        "parameters": {
            "type": "object",
            "required": ["day_of_week", "hours_of_day"],
            "properties": {
                "day_of_week": {"type": "integer", "description": "Day of week (1=Monday, ..., 7=Sunday)"},
                "hours_of_day": {
                    "type": "array",
                    "description": "Vector of hours to predict (0-23), e.g. [0,1,2,...,23].",
                    "items": {"type": "integer"},
                },
            }
        }
    }
}

# 4. RUN AGENT ###################################

messages = [
    {
        "role": "system",
        "content": (
            "You are a Brussels traffic assistant. "
            "Always report units clearly as vehicles observed in one representative minute "
            "(1m/t1 interval) within the requested hour and day of week. "
            "Call predict_vehicle_count using day_of_week and hours_of_day vector."
        ),
    },
    {
        "role": "user",
        "content": "Predict Brussels vehicle count for Monday for every hour (0 through 23).",
    }
]
tools = [tool_predict_vehicle_count]

result = agent(
    messages=messages,
    model=MODEL,
    output="text",
    tools=tools
)

print("Agent result:", result)

# 5. VERIFY ###################################

direct = predict_vehicle_count(day_of_week=1, hours_of_day=list(range(24)))
print("Direct API call predictions returned:", len(direct["predictions"]))
print(f"Sample one-minute vehicle count: {direct['predictions'][8]['predicted_vehicle_count']} (1m/t1 at Monday 08:00)")
print("Unit:", UNIT_NOTE)
print("Match:", str(direct["predictions"][8]["predicted_vehicle_count"]) in str(result))
