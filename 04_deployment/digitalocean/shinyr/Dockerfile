# Minimal Shiny for R on DigitalOcean App Platform
# Base: Posit's official rocker/shiny image
FROM rocker/shiny:latest

WORKDIR /app

# Copy app files
COPY app.R .

# Expose port (DigitalOcean App Platform may set PORT env var)
EXPOSE 3838

# Run Shiny app directly (similar to shinypy approach)
# Listen on all interfaces for container hosting
CMD ["R", "-e", "shiny::runApp('/app', host='0.0.0.0', port=as.numeric(Sys.getenv('PORT', 3838)))"]
