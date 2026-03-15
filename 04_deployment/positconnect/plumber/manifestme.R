# workflow.R

# Optional script to create a manifest file for deployment to Posit Connect
# install.packages("rsconnect")
rsconnect::writeManifest(appDir = "04_deployment/positconnect/plumber", appMode = "api")
