# deployme.R
# Deploy the Brussels Plumber endpoint to Posit Connect.
# Tim Fraser
# Rscript 12_end/03_plumber/deployme.R

library(rsconnect)

readRenviron(".env")

APP_DIR = "12_end"
SERVER_NAME = "connect-fraser"

rsconnect::addServer(
  url = Sys.getenv("CONNECT_SERVER"),
  name = SERVER_NAME
)

if (!file.exists(file.path(APP_DIR, "manifest.json"))) {
  rsconnect::writeManifest(
    appDir = APP_DIR,
    appMode = "api",
    appPrimaryDoc = "03_plumber/plumber.R",
    forceGeneratePythonEnvironment = TRUE
  )
}

# Deploy the api!
rsconnect::deployAPI(
  api = APP_DIR,
  server = SERVER_NAME,
  appName = Sys.getenv("CONNECT_TITLE", unset = "brussels-traffic-plumber"),
  forceUpdate = TRUE
)
