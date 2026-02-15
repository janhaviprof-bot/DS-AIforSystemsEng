# 03_ollama_cloud.py
# Query Ollama Cloud Models with API Key
# This script demonstrates how to query Ollama's cloud-hosted models
# using your API key stored in the .env file

# If you haven't already, install these packages...
# pip install requests python-dotenv

# Load libraries
import requests  # For HTTP requests
import json      # For working with JSON
import os        # For environment variables
from dotenv import load_dotenv  # For loading .env file

# Starting message
print("\n🚀 Querying Ollama Cloud in Python...\n")

# Load environment variables from .env file
# This reads the .env file and loads variables into the environment
load_dotenv()

# Get API key from environment variable
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")

# Check if API key is set
if not OLLAMA_API_KEY:
    raise ValueError("OLLAMA_API_KEY not found in .env file. Please set it up first.")

# Ollama Cloud API endpoint
url = "https://ollama.com/api/chat"

# Construct the request body
body = {
    "model": "gpt-oss:20b-cloud",  # Low-cost cloud model
    "messages": [
        {
            "role": "user",
            "content": "Hello! Please respond with: Model is working Janhavi."
        }
    ],
    "stream": False  # Non-streaming response
}

# Set headers with API key
headers = {
    "Authorization": f"Bearer {OLLAMA_API_KEY}",
    "Content-Type": "application/json"
}

# Send POST request to Ollama Cloud API
response = requests.post(url, headers=headers, json=body)

# Check if request was successful
response.raise_for_status()

# Parse the response JSON
result = response.json()

# Extract the model's reply
output = result["message"]["content"]

# Print the model's reply
print("📝 Model Response:")
print(output)
print()

# Closing message
print("✅ Ollama Cloud query complete.\n")

# Clear environment
globals().clear()
