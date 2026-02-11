# 02_ollama.py
# Query Ollama LLM
# Pairs with 02_ollama.R
# Tim Fraser

# This script demonstrates how to query a local Ollama LLM instance using Python.
# Students will learn how to make HTTP POST requests to interact with language models
# running locally on their machine.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import requests  # for HTTP requests
import json      # for working with JSON

# Starting message
print("\n🚀 Sending LLM query in Python...\n")

# If you haven't already, install the requests package...
# pip install requests

## 0.2 Configure Connection #########################

# Set the port where Ollama is running
PORT = 11434
OLLAMA_HOST = f"http://localhost:{PORT}"
url = f"{OLLAMA_HOST}/api/generate"

## 0.3 Construct Request Body #######################

# Build the request body as a dictionary
# This tells Ollama which model to use and what prompt to send
body = {
    "model": "smollm2:1.7b",  # Model name
    "prompt": "Is model working?",  # User prompt
    "stream": False  # Non-streaming response
}

# 1. SEND REQUEST ###################################

# Build and send the POST request to the Ollama REST API
# The requests library makes it easy to send HTTP requests
response = requests.post(url, json=body)

# 2. PARSE RESPONSE ################################

# Parse the response JSON
# The response from Ollama is in JSON format
response_data = response.json()

# Extract the model's reply as a string
# The response structure contains the generated text
output = response_data["response"]

# Print the model's reply
print(output)

# Closing message
print("\n✅ LLM query complete. Exiting Python...\n")
