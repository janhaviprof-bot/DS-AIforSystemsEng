# deployme.py
# Deploy the MCP Server to Posit Connect (Python)
# Pairs with mcp_plumber/deployme.R
# Tim Fraser

# Posit Connect can host Python APIs (FastAPI/Flask) just like R Plumber APIs.
# This script shows two deployment paths:
#   A. rsconnect-python CLI  (recommended for Connect)
#   B. Docker + DigitalOcean (if you don't have Connect)

# 0. PREREQUISITES #########################################################

# pip install rsconnect-python python-dotenv

# requirements.txt in this folder (fastapi, uvicorn, pandas, …) is used for the bundle.

import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths: this file lives in mcp_fastapi/, so the app dir does not depend on shell cwd.
APP_DIR = Path(__file__).resolve().parent

# Match mcp_plumber/deployme.R: CONNECT_SERVER, CONNECT_API_KEY (optional: CONNECT_URL fallback)
CONNECT_SERVER = os.environ.get("CONNECT_SERVER") or os.environ.get(
    "CONNECT_URL", "https://your-connect-server.com"
)
CONNECT_API_KEY = os.environ.get("CONNECT_API_KEY", "YOUR_KEY_HERE")

# 1. CONFIGURE CONNECT #####################################################

subprocess.run([
    "rsconnect", "add",
    "--server",  CONNECT_SERVER,
    "--api-key", CONNECT_API_KEY,
    "--name",    "my-connect",
], check=True)

# 1.2 Write manifest (rsconnect defaults to entrypoint "app"; we use server:app)
subprocess.run([
    "rsconnect", "write-manifest", "api",
    "--entrypoint", "server:app",
    "--overwrite",
    str(APP_DIR),
], check=True)

# 2. DEPLOY ################################################################

subprocess.run([
    "rsconnect", "deploy", "fastapi",
    "--title",      "mcp-py-summarizer",
    "--server",     CONNECT_SERVER,
    "--api-key",    CONNECT_API_KEY,
    "--entrypoint", "server:app",
    str(APP_DIR),
], check=True)

# After deployment, Connect gives you a URL like:
#   https://your-connect-server.com/content/<id>/
# Your MCP endpoint is:
#   https://your-connect-server.com/content/<id>/mcp

# 3. ALTERNATIVE: DOCKER + DIGITALOCEAN ###################################

# If you prefer DigitalOcean (or any VPS), create a Dockerfile:
#
# FROM python:3.12-slim
# WORKDIR /app
# COPY requirements.txt .
# RUN pip install -r requirements.txt
# COPY server.py .
# CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
#
# Then:
#   docker build -t mcp-py-summarizer .
#   docker run -p 8000:8000 mcp-py-summarizer
#
# Push to DigitalOcean App Platform or a Droplet with Docker installed.
# Your /mcp endpoint is then: http://<your-droplet-ip>:8000/mcp

# 4. MCP CLIENT CONFIG #####################################################

# Once deployed, add to your MCP client (e.g., Claude Desktop):
#
# {
#   "mcpServers": {
#     "py-summarizer": {
#       "url": "https://your-connect-server.com/content/<id>/mcp",
#       "headers": { "Authorization": "Key YOUR_CONNECT_API_KEY" }
#     }
#   }
# }
