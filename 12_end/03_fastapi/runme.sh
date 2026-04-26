#!/bin/bash
# runme.sh
# Run FastAPI app locally with uvicorn.
# Run from anywhere: bash 12_end/fastapi/runme.sh

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

python -m uvicorn main:app --host 0.0.0.0 --port 8000
