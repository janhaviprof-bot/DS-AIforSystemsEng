# testme.py
# Smoke-test the deployed agent (Posit Connect or any public base URL)
# Tim Fraser
#
# Requires AGENT_PUBLIC_URL in .env (deployed base, no trailing slash).
# For local runs, start the API first: ./runme.sh or: python -m uvicorn app.api:app (see README).
#
# Deploy workflow (see also README, manifestme.sh, deployme.sh):
#   pip install rsconnect-python
#   ./manifestme.sh   # uses --entrypoint app.api:app
#   ./deployme.sh
#
# On Connect, set at least: OLLAMA_API_KEY, OLLAMA_HOST, OLLAMA_MODEL.
#
# pip install requests python-dotenv

import os
import sys

import requests
from dotenv import load_dotenv


def main() -> None:
    _here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(_here)
    load_dotenv()

    base = os.getenv("AGENT_PUBLIC_URL", "").rstrip("/")
    if not base:
        print(
            "Set AGENT_PUBLIC_URL in .env to your deployed base, "
            "e.g. https://connect.example.com/content/abc",
            file=sys.stderr,
        )
        sys.exit(1)

    headers = {"Content-Type": "application/json"}

    print(f"# Smoke test at {base}\n")

    r = requests.get(f"{base}/health", timeout=30)
    print("health:", r.status_code, r.json())

    r2 = requests.post(
        f"{base}/hooks/agent",
        headers=headers,
        json={
            "task": (
                "Training brief: incident 'Exercise Riverdale', River County, last 24h — "
                "minimal situational sections; note if no live search."
            ),
        },
        timeout=120,
    )
    print("agent:", r2.status_code, r2.text[:500])


if __name__ == "__main__":
    main()
