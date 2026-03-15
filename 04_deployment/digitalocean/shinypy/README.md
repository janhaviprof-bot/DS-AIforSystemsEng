# Shiny for Python Example

A minimal Shiny for Python web application for DigitalOcean App Platform deployment.

## What This App Does

This is a simple interactive Shiny web application built with Python. It features:
- A sidebar with a slider to control the number of points (1-100)
- A text input field for a custom label
- A reactive output card that displays the label and current slider value

The app demonstrates Shiny's reactive programming model where UI inputs automatically update outputs.

## File Structure

- **`app.py`** - Main Shiny application with UI and server logic
- **`requirements.txt`** - Python dependencies (shiny package)
- **`Dockerfile`** - Container configuration using Python 3.12-slim base image
- **`testme.sh`** - Local testing script

## How to Test

Run the test script to start the app locally:

```bash
./testme.sh
```

Or manually:

```bash
cd 04_deployment/digitalocean/shinypy
python -m shiny run app.py --host 0.0.0.0 --port 8000
```

Once running, open your browser to `http://localhost:8000` to interact with the app. Adjust the slider and text input to see the reactive output update.
