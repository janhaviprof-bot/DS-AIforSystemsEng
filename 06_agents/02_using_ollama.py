# 02_using_ollama.py
# Using Ollama with System Prompts
# Pairs with 02_using_ollamar.R
# Tim Fraser

# This script demonstrates how to use Ollama in Python to interact with an LLM.
# Students will learn how to create system prompts and manage chat history.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import requests  # for HTTP requests
import json      # for working with JSON
import time      # for timing operations

# If you haven't already, install the requests package...
# pip install requests

## 0.2 Configure Connection #########################

# Select model of interest
MODEL = "smollm2:1.7b"

# Set the port where Ollama is running
PORT = 11434
OLLAMA_HOST = f"http://localhost:{PORT}"
url = f"{OLLAMA_HOST}/api/chat"

# 1. CHECK MODEL ###################################

# Check if model is available
# Note: In Python, we'll assume the model is already pulled
# You can check models with: ollama list (via command line)

# 2. CREATE MESSAGES ###################################

# Create a list of messages for the chat
# System prompt defines the agent's role and behavior
messages = [
    {
        "role": "system",
        "content": """You are a talking cat. Your name is Yoda.You are an ancient Philosopher. You can only talk about philosophy and ancient wisdom.
        You are a cat who dedicated his life to science and reson behind the AI development in the world"""
    },
    {
        "role": "user",
        "content": "Hello, what can you tell someone in their 20s about life?"
    }
]

# 3. SEND CHAT REQUEST ###################################

# Build the request body
body = {
    "model": MODEL,
    "messages": messages,
    "stream": False  # Non-streaming response
}

# Time the request
start_time = time.time()

# Send POST request to Ollama chat API
response = requests.post(url, json=body)

# Check if request was successful
response.raise_for_status()

# Parse the response JSON
response_data = response.json()

# Extract the assistant's reply
resp = response_data["message"]["content"]

# Calculate elapsed time
elapsed_time = time.time() - start_time

# 4. APPEND TO CHAT HISTORY ###################################

# Append the assistant's response to the message history
messages.append({
    "role": "assistant",
    "content": resp
})

# 5. VIEW RESULTS ###################################

# View the response
print("📝 Model Response:")
print(resp)
print()

# View the chat history
print("💬 Full Chat History:")
for msg in messages:
    print(f"{msg['role'].upper()}: {msg['content']}")
    print()

# View timing information
print(f"⏱️  Request took {elapsed_time:.2f} seconds")
