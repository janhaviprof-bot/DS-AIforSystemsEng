# Plumber API Example

A minimal Plumber REST API application for Posit Connect deployment.

## What This App Does

This is a simple Plumber API (R's equivalent to Flask/FastAPI) that provides several REST endpoints:
- `GET /echo` - Echo back a message parameter
- `GET /plot` - Generate and return a histogram plot as PNG
- `POST /sum` - Calculate the sum of two numbers

The API uses unboxed JSON serialization for cleaner response formatting.

## File Structure

- **`plumber.R`** - Main Plumber API file with route definitions and annotations

## How to Test

To test locally, you'll need R and the plumber package installed. Run:

```r
library(plumber)
pr <- plumber::plumb("plumber.R")
pr$run(host = "0.0.0.0", port = 8000)
```

Once running, test the endpoints:
- `http://localhost:8000/echo?msg=hello` - Test echo endpoint
- `http://localhost:8000/plot` - View generated histogram
- `http://localhost:8000/sum?a=5&b=3` - Test sum endpoint (POST)

## Deployment to Posit Connect

This app can be deployed to Posit Connect using GitHub Actions. See [ACTIVITY: Deploy to Posit Connect via GitHub Actions](../ACTIVITY_posit_connect_github_actions.md) for instructions.
