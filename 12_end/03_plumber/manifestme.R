# manifestme.R
# Write manifest.json for Posit Connect deployment of this Plumber API.
# Tim Fraser
# Rscript 12_end/03_plumber/manifestme.R


rsconnect::writeManifest(
  appDir = "12_end",
  appMode = "api",
  appPrimaryDoc = "03_plumber/plumber.R",
  forceGeneratePythonEnvironment = TRUE
)
