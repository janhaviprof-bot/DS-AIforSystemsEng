# SWAPI Star Wars Dashboard — one-line launcher
# Run this file to start the Shiny app (e.g. Rscript run.R or source("run.R")).

if (!requireNamespace("shiny", quietly = TRUE)) {
  install.packages("shiny", repos = "https://cloud.r-project.org")
}
library(shiny)

runApp(appDir = ".", appFile = "app.R")
