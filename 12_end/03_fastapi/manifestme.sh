#!/bin/bash
# manifestme.sh
# Write manifest.json for Posit Connect deployment of this FastAPI app.
# Run from anywhere: bash 12_end/fastapi/manifestme.sh

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

pip install -q rsconnect-python
rsconnect write-manifest fastapi --entrypoint main:app --overwrite .
