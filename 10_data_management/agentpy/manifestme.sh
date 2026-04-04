#!/bin/bash
# manifestme.sh
# Write manifest.json for Posit Connect deployment of this FastAPI app.
# Run from anywhere: bash 10_data_management/agentpy/manifestme.sh
# Or: cd 10_data_management/agentpy && ./manifestme.sh

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

pip install -q rsconnect-python
rsconnect write-manifest api --entrypoint app.api:app --overwrite .
