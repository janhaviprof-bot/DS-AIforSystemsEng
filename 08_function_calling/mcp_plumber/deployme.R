# deployme.R
# Deploy the MCP Server to Posit Connect (R)
# Pairs with mcp_fastapi/deployme.py
# Tim Fraser

# This script deploys plumber.R to Posit Connect as a Plumber API.
# Once deployed, any MCP-compatible client can point to its /mcp endpoint.

# 0. SETUP ###################################

# Install rsconnect if needed:
#   install.packages("rsconnect")
library(rsconnect)

# 1. CONFIGURE YOUR CONNECT SERVER ########################################

# Set your Posit Connect credentials once per machine.
# Find your API key under: Connect → Account → API Keys

# Read the .env file
readRenviron(".env")

# Replace these values with your own:
rsconnect::addServer(
  url  = Sys.getenv("CONNECT_SERVER"),
  name = "connect-fraser"          # a local nickname
)


# 2. DEPLOY ################################################################

if(!file.exists("manifest.json")) { rsconnect::writeManifest(appDir = "08_function_calling/mcp_plumber", appMode = "api", appPrimaryDoc = "plumber.R") }
# deployAPI() packages plumber.R and pushes it to Connect.
# appName becomes part of the URL path.

rsconnect::deployAPI(
  api        = "08_function_calling/mcp_plumber",  # folder containing plumber.R
  server     = "posit_connect",
  appName    = "mcp-r-summarizer",
  forceUpdate = TRUE
)

# After deployment, Connect gives you a content URL like:
#   https://your-connect-server.com/content/<id>/
#
# Your MCP endpoint is:
#   https://your-connect-server.com/content/<id>/mcp
#
# 3. USE THE DEPLOYED SERVER ###############################################

# Add to your MCP client config (e.g., Claude Desktop ~/.config/claude/claude_desktop_config.json):
#
# {
#   "mcpServers": {
#     "r-summarizer": {
#       "url": "https://connect.systems-apps.com/plumbermcp/mcp",
#       "headers": { "Authorization": "Key YOUR_CONNECT_API_KEY" }
#     }
#   }
# }
#
# Or point testme.R at the deployed URL instead of localhost.
