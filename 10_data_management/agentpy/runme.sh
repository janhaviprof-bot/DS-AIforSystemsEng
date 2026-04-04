#!/bin/bash
# runme.sh
# Run the agent FastAPI app locally with uvicorn (same as README quick start).
# Run from anywhere: bash 10_data_management/agentpy/runme.sh
# Or: cd 10_data_management/agentpy && ./runme.sh

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

python -m uvicorn app.api:app --host 0.0.0.0 --port 8000
# Open app in localhost:8000/docs/ in browser
