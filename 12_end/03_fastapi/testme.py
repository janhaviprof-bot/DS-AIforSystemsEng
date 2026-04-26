# testme.py
# Smoke-test the FastAPI prediction endpoint.
# Tim Fraser
#
# Optional .env:
# - API_PUBLIC_URL (default: http://localhost:8000)
#
# pip install requests python-dotenv

import os
from pathlib import Path

import requests
from dotenv import load_dotenv


def main() -> None:
    here = Path(__file__).resolve().parent
    os.chdir(here)
    load_dotenv()

    base = os.getenv("API_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    url = f"{base}/predict"
    params = {"day_of_week": 1, "hour_of_day": 8}

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    print("status:", response.status_code)
    print("url:", response.url)
    print("body:", response.json())


if __name__ == "__main__":
    main()
