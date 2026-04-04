#!/bin/sh
# pingme.sh — example curl against MCP ping (pairs with test flow in README)
# Tim Fraser
#
# Usage:
#   export MCP_URL="http://127.0.0.1:8000/mcp"   # or your Connect .../mcp URL
#   export CONNECT_API_KEY="your_viewer_key"       # only if the server requires it
#   sh 08_function_calling/mcp_plumber/pingme.sh
#
# Do not commit real API keys. For local Plumber, omit CONNECT_API_KEY.

set -eu

MCP_URL="${MCP_URL:-http://127.0.0.1:8000/mcp}"

if [ -n "${CONNECT_API_KEY:-}" ]; then
  curl -sS -X POST "${MCP_URL}" \
    -H "Content-Type: application/json" \
    -H "Authorization: Key ${CONNECT_API_KEY}" \
    -d '{"jsonrpc":"2.0","id":1,"method":"ping"}'
else
  curl -sS -X POST "${MCP_URL}" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":1,"method":"ping"}'
fi
echo
