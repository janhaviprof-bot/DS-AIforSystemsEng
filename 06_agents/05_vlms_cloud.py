# 05_vlms_cloud.py
# Using Visual Language Models (VLMs) with Ollama Cloud
# Pairs with 05_vlms_cloud.R
# Tim Fraser
#
# Topic: Visual Language Models
#
# What if our AI systems could see, not just read?
# This script shows how to send an image to a vision-capable model
# (like gemma3:4b) using Ollama cloud.
#
# Read about model details in the Ollama library:
# https://ollama.com/library/gemma3

# If you haven't already, install these packages...
# pip install requests pillow python-dotenv

# 0. SETUP ###################################

## Example Image #################################

# Today, we'll use an example image from Unsplash.
# (Great place to get free pictures for your projects!)
# Photo by Toa Heftiba
# Source Link: https://unsplash.com/photos/people-eating-inside-of-cafeteria-during-daytime-6bKpHAun4d8
# Creator Link: https://unsplash.com/@heftiba
#
# It shows a bunch of people in a coffee shop.
#
# Let's say we want to count the number of people in the image.
# There are creepy uses of this, sure, but also some legitimate uses:
# - evacuation checks
# - crowd detection
# - object detection
# - face detection
# - text detection
# - license plate detection
# - car detection
# - pedestrian detection
#
# An ethical system would perform the count, and then delete the image.
# That way, we reduce the risk of the image being reused for harmful purposes.

## 0.1 Load Packages #################################

import base64  # for image encoding before API upload
import json  # for parsing machine-readable model output
import os  # for environment variables and file checks

import requests  # for HTTP requests
from dotenv import load_dotenv  # for loading .env files
from PIL import Image  # for image resizing

## 0.2 Image Processing #################################

# First step: downscale the image.
# Why? Vision models still have context limits, so huge images can be wasteful
# or fail. Smaller images are often enough for counting tasks.

# Path to the original image we want the VLM to analyze
image_path = "06_agents/05_coffeeshop.jpg"

if not os.path.exists(image_path):
    raise FileNotFoundError(f"Image not found: {image_path}")

# Shrink image to 50% of the original size
with Image.open(image_path) as img:
    width, height = img.size
    new_size = (max(1, int(width * 0.5)), max(1, int(height * 0.5)))
    img_small = img.resize(new_size)
    image_path_small = "06_agents/05_coffeeshop_small.jpg"
    img_small.save(image_path_small)

print(f"Saved resized image: {image_path_small} ({new_size[0]}x{new_size[1]})")

## 0.3 Environment #################################

# Load .env (contains OLLAMA_API_KEY for cloud access)
if os.path.exists(".env"):
    load_dotenv()
else:
    print(".env file not found. Make sure it exists in the project root.")

ollama_api_key = os.getenv("OLLAMA_API_KEY")
if not ollama_api_key:
    raise ValueError("OLLAMA_API_KEY not found in .env file.")

## 0.4 Configuration #################################

# gemma3:4b is a multimodal model that can read images + text
model = "gemma3:4b"
# Prompt we pair with the image
prompt = "Analyze this image and count the number of people in the image."

# Make sure the downscaled image exists before sending
if not os.path.exists(image_path_small):
    raise FileNotFoundError(f"Image not found: {image_path_small}")

# Let's write ourselves a short helper function for the query
def query(image_file_path, user_prompt, model_name, api_key):
    """Send one image + prompt to Ollama Cloud and return text output."""
    with open(image_file_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # Build the request body (Ollama chat format)
    body = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": user_prompt,
                "images": [image_base64],
            }
        ],
        "stream": False,
    }

    # Send bearer-token auth in request headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # POST to Ollama Cloud
    response = requests.post("https://ollama.com/api/chat", headers=headers, json=body, timeout=120)
    response.raise_for_status()
    result = response.json()
    return result["message"]["content"]


# 1. CLOUD VLM WITH REQUESTS ##########################

output = query(image_path_small, prompt, model, ollama_api_key)
print("\nVLM Response (cloud):")
print(output)

# 2. MACHINE READABLE OUTPUT #########################

# Often, in production workflows, we want machine-readable output.
# A good pattern is to ask the model to return only a JSON string.
prompt2 = (
    "Analyze this image and count the number of people in the image. "
    "Output the answer in a JSON string. "
    "Do not include any other text in your response. "
    "Do not include any extra formatting like '```json' in your response. "
    "The JSON string should have the following format: "
    '{"n_sitting":"<total number of people sitting here>","n_standing":"<total number of people standing here>"}'
)

resp2 = query(image_path_small, prompt2, model, ollama_api_key)
print("\nRaw JSON-like response:")
print(resp2)

try:
    # Parse the JSON string into a Python dictionary
    parsed_json = json.loads(resp2)
    print("\nParsed JSON:")
    print(parsed_json)
    print(f"Number of people sitting: {parsed_json.get('n_sitting')}")
    print(f"Number of people standing: {parsed_json.get('n_standing')}")
except json.JSONDecodeError:
    print("\nCould not parse JSON response. Try rerunning the query for stricter formatting.")
