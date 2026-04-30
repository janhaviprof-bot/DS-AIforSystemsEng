#!/bin/bash
# runme.sh
# Run FastAPI app locally with uvicorn.
# Run from repo root: bash 12_end/03_fastapi/runme.sh

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

python -m uvicorn main:app --host 0.0.0.0 --port 8000
