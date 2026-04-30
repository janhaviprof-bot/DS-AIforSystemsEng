#!/bin/bash
# manifestme.sh
# Write manifest.json for Posit Connect deployment of this FastAPI app.
# Run from repo root: bash 12_end/03_fastapi/manifestme.sh

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

mkdir -p data
cp -f "../data/modelpy.json" "../data/validationpy.json" data/

pip install -q rsconnect-python
rsconnect write-manifest fastapi --entrypoint main:app --overwrite . --exclude ".env"
