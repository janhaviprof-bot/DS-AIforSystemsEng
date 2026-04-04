# manifestme.R

# Optional script to create a manifest file for deployment to Posit Connect
# (same idea as 04_deployment/positconnect/plumber/manifestme.R; includes Python env for reticulate).
# Tim Fraser
#
# Run from the repository root (getwd() = dsai).
#
# install.packages("rsconnect")

rsconnect::writeManifest(
  appDir = "10_data_management/agentr",
  appMode = "api",
  appPrimaryDoc = "plumber.R",
  forceGeneratePythonEnvironment = TRUE
)
