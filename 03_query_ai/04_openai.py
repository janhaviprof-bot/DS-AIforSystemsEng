# 04_openai.py
# Query OpenAI Models with API Key
# This script demonstrates how to query OpenAI's models
# using your API key stored in the .env file

# If you haven't already, install these packages...
# pip install requests python-dotenv

# Load libraries
import requests # for HTTP requests
import os # for environment variables
from dotenv import load_dotenv # for loading .env file
import time # for optional async queries

# Starting message
print("\n🚀 Querying OpenAI in Python...\n")

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# Check if API key is set
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file. Please set it up first.")

# OpenAI API endpoint
url = "https://api.openai.com/v1/responses"

# Construct the request body
body = {
    "model": "gpt-4o-mini",  # Low-cost model
    "input": "Hello! Please respond with: Model is working."
}

# Set headers with API key
headers = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json"
}

# Send POST request to OpenAI API
response = requests.post(url, headers=headers, json=body)
response.raise_for_status()

# Parse the response JSON
result = response.json()

# Optional - for longer queries...
# Wait for the response to finish (OpenAI returns right away, then we poll until done)
# while result.get("status") in ("created", "in_progress"):
#     time.sleep(0.5)
#     r = requests.get(f"https://api.openai.com/v1/responses/{result['id']}", headers=headers)
#     r.raise_for_status()
#     result = r.json()

# Gross, but straightforward version of extracting the model's reply
output = result['output'][0]['content'][0]['text']


# Print the model's reply
print("📝 Model Response:")
print(output)
print()

# Closing message
print("✅ OpenAI query complete.\n")
