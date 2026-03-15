# manifestme.R
# Write a manifest.json file for a Shiny R app,
# for deploying to Posit Connect.
# install.packages("rsconnect")

rsconnect::writeManifest(appDir = "04_deployment/positconnect/shinyr", appMode = "shiny")
