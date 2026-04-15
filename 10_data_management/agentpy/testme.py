# testme.py
# Smoke-test the deployed agent (Posit Connect or any public base URL)
# Tim Fraser
#
# Requires AGENT_PUBLIC_URL in .env (deployed base, no trailing slash).
# For local runs, start the API first: ./runme.sh or: python -m uvicorn app.api:app (see README).
#
# Deploy workflow (see also README, manifestme.sh, deployme.sh):
#   pip install rsconnect-python
#   ./manifestme.sh   # uses rsconnect write-manifest fastapi --entrypoint app.api:app
#   ./deployme.sh
#
# On Connect, set at least: OLLAMA_API_KEY, OLLAMA_HOST, OLLAMA_MODEL.
#
# pip install requests python-dotenv

import os
import sys

import requests
from dotenv import load_dotenv


def print_response(label: str, response: requests.Response) -> None:
    """Print JSON when available; otherwise print a text preview."""
    content_type = response.headers.get("Content-Type", "")
    print(f"{label}:", response.status_code)
    try:
        print(response.json())
    except ValueError:
        text_preview = response.text[:500].strip()
        print(
            f"(non-JSON response, content-type={content_type or 'unknown'}) "
            f"{text_preview}"
        )


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
    # If testing locally instead of a deployed URL, set:
    # base = "http://localhost:8000"
    # If testing the instructor deployment, set:
    # base = "https://connect.systems-apps.com/autonomous_agent"

    headers = {"Content-Type": "application/json"}
    connect_viewer_key = os.getenv("CONNECT_VIEWER_KEY", "").strip()
    # If CONNECT_VIEWER_KEY is set in .env, include Bearer auth automatically.
    # Keep this for secured deployments (common on Connect); unset for public endpoints.
    if connect_viewer_key:
        headers["Authorization"] = f"Bearer {connect_viewer_key}"

    print(f"# Smoke test at {base}\n")

    # If /health is also protected in your deployment, keep `headers=headers`.
    # If /health is public, you can remove `headers=headers` from this call.
    r = requests.get(f"{base}/health", headers=headers, timeout=30)
    print_response("health", r)
    if r.status_code in {401, 403}:
        print(
            "Hint: endpoint requires auth. Add CONNECT_VIEWER_KEY to .env "
            "or use a public/local AGENT_PUBLIC_URL."
        )

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
    print_response("agent", r2)


if __name__ == "__main__":
    main()
