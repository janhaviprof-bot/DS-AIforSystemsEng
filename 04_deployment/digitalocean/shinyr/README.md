# Shiny for R Example

A minimal Shiny for R web application for DigitalOcean App Platform deployment.

## What This App Does

This is a simple interactive Shiny web application built with R. It displays a histogram of the Old Faithful Geyser's waiting times between eruptions. The app features:
- A sidebar with a slider to control the number of histogram bins (1-50)
- A main panel showing the histogram plot
- A text output displaying the current number of bins

The app uses R's built-in `faithful` dataset and demonstrates Shiny's reactive programming where changing the slider automatically updates the histogram.

## File Structure

- **`app.R`** - Main Shiny application with UI and server logic
- **`workflow.R`** - Optional testing script for developing functions before integrating into the Shiny app
- **`Dockerfile`** - Container configuration using rstudio/shiny base image
- **`testme.sh`** - Local testing script

## How to Test

Run the test script to start the app locally:

```bash
./testme.sh
```

Or manually:

```bash
cd 04_deployment/digitalocean/shinyr
Rscript -e "shiny::runApp('app.R', host='0.0.0.0', port=3838)"
```

Once running, open your browser to `http://localhost:3838` to interact with the app. Adjust the slider to change the number of bins in the histogram.
