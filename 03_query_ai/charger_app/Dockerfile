# EV Charger Shiny app – production image for DigitalOcean App Platform
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY app.py ui_components.py server.py utils.py ./

EXPOSE 8080

# Run Shiny on 0.0.0.0:8080 (required for App Platform)
CMD ["shiny", "run", "app.py", "--host", "0.0.0.0", "--port", "8080"]
