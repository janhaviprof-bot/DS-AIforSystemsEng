#!/bin/bash
# deployme.sh
# Deploy this FastAPI folder to Posit Connect via rsconnect-python.
# Requires .env in this folder with CONNECT_SERVER and CONNECT_API_KEY.
# On Windows without Bash, use deployme.ps1 in this same folder.

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${CONNECT_SERVER:?Set CONNECT_SERVER in .env (Posit Connect URL)}"
: "${CONNECT_API_KEY:?Set CONNECT_API_KEY in .env}"

mkdir -p data
cp -f "../data/modelpy.json" "../data/validationpy.json" data/

pip install -q rsconnect-python

TITLE="${CONNECT_TITLE:-brussels-traffic-fastapi}"

rsconnect deploy fastapi \
  --title "$TITLE" \
  --server "$CONNECT_SERVER" \
  --api-key "$CONNECT_API_KEY" \
  --entrypoint main:app \
  --exclude ".env" \
  .
