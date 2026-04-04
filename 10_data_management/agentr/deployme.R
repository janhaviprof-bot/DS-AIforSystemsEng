# deployme.R
# Deploy the disaster situational brief agent (Plumber) to Posit Connect (R)
# Pairs with agentpy/deployme.sh (FastAPI)
# Tim Fraser
#
# This script deploys plumber.R to Posit Connect as a Plumber API (same pattern as
# 08_function_calling/mcp_plumber/deployme.R). Includes requirements.txt for reticulate / crewai_tools.
#
# Run from the repository root (getwd() = dsai). Ensure .env has CONNECT_SERVER and CONNECT_API_KEY,
# or place .env in this folder and setwd here before sourcing.

# 0. SETUP ###################################

# install.packages("rsconnect")
library(rsconnect)

# 1. CONFIGURE YOUR CONNECT SERVER ########################################

# Set your Posit Connect credentials once per machine.
# Find your API key under: Connect → Account → API Keys

# Read the .env file
readRenviron(".env")

APP_DIR = "10_data_management/agentr"

# Replace these values with your own:
rsconnect::addServer(
  url  = Sys.getenv("CONNECT_SERVER"),
  name = "connect-fraser" # a local nickname
)


# 2. MANIFEST ################################################################

if (!file.exists(file.path(APP_DIR, "manifest.json"))) {
  rsconnect::writeManifest(
    appDir = APP_DIR,
    appMode = "api",
    appPrimaryDoc = "plumber.R",
    forceGeneratePythonEnvironment = TRUE
  )
}


# 3. DEPLOY ################################################################

# deployAPI() packages plumber.R and pushes it to Connect.
# appName becomes part of the URL path (override with CONNECT_TITLE in .env).

rsconnect::deployAPI(
  api         = APP_DIR,
  server      = "connect-fraser",
  appName     = Sys.getenv("CONNECT_TITLE", unset = "course-autonomous-agent-r"),
  forceUpdate = TRUE
)

# After deployment, Connect gives you a content URL like:
#   https://your-connect-server.com/content/<id>/
#
# Use GET /health and POST /hooks/agent on that base (see README.md, testme.R).
