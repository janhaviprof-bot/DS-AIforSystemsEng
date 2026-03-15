# Minimal Shiny for Python on DigitalOcean App Platform
# Base: official Python image (Posit supports Python 3.8+; 3.12 is current LTS)
FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app.py .

# Listen on all interfaces for container hosting (App Platform may set PORT)
EXPOSE 8000
CMD ["shiny", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
