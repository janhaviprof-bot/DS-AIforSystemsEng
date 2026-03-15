# 05_vlms_local.py
# Using Visual Language Models (VLMs) with Ollama (local)
# Pairs with 05_vlms_local.R
# Tim Fraser
#
# Topic: Visual Language Models
#
# What if our AI systems could see, not just read?
# This script shows how to send an image to a vision-capable model
# (like llava) using local Ollama.
#
# Read about model details in the Ollama library:
# https://ollama.com/library/llava
#
# NOTE:
# Running vision queries can take a LONG time on a local machine.
# You might want to use the cloud version instead.

# If you haven't already, install these packages...
# pip install requests pillow

# 0. SETUP ###################################

## Example Image #################################

# Today, we'll be using an example image from Unsplash.
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
import os  # for environment variables and file checks
import subprocess  # for launching ollama serve from Python
import tempfile  # for temporary Ollama log files
import time  # for short waits during server startup

import requests  # for HTTP requests
from PIL import Image  # for image resizing

## 0.2 Image Processing #################################

# First step: we need to downscale the image.
# This is because the model has a context limit.
# We usually don't need full-resolution images for counting tasks.

# Path to the original image we want the VLM to analyze
image_path = "06_agents/05_coffeeshop.jpg"

if not os.path.exists(image_path):
    raise FileNotFoundError(f"Image not found: {image_path}")

# Shrink the image to 50% of the original size
with Image.open(image_path) as img:
    width, height = img.size
    new_size = (max(1, int(width * 0.5)), max(1, int(height * 0.5)))
    img_small = img.resize(new_size)
    image_path_small = "06_agents/05_coffeeshop_small.jpg"
    img_small.save(image_path_small)

print(f"Saved resized image: {image_path_small} ({new_size[0]}x{new_size[1]})")

## 0.3 Configuration #################################

# LLaVA is a multimodal model that can read images AND text.
# Remember, you'll need to pull the model first:
# ollama pull llava
model = "llava"
# Prompt paired with the image
prompt = "Analyze this image and count the number of people in the image."

# Local Ollama connection details
port = 11434
ollama_host = f"http://127.0.0.1:{port}"
ollama_process = None


def is_ollama_running(host_url):
    """Check whether a local Ollama server is already responding."""
    try:
        response = requests.get(f"{host_url}/api/tags", timeout=2)
        return response.status_code == 200
    except requests.RequestException:
        return False


def start_ollama_server():
    """Start ollama serve in the background if needed."""
    global ollama_process

    if is_ollama_running(ollama_host):
        print("Ollama server already running; reusing existing process.")
        return

    # Write server output to a temporary log file.
    log_file = tempfile.NamedTemporaryFile(prefix="ollama_serve_", suffix=".log", delete=False)
    log_path = log_file.name
    log_file.close()

    # Set environment variables for the server process.
    env = os.environ.copy()
    env["OLLAMA_HOST"] = f"127.0.0.1:{port}"
    env["OLLAMA_CONTEXT_LENGTH"] = "32000"

    # Start `ollama serve` asynchronously so Python stays usable.
    with open(log_path, "a", encoding="utf-8") as log_handle:
        ollama_process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=log_handle,
            stderr=log_handle,
            env=env,
        )

    # Wait briefly for server readiness before the first query.
    time.sleep(0.5)
    print(f"Started ollama serve (pid={ollama_process.pid}). Log: {log_path}")


def query_local(image_file_path, user_prompt, model_name):
    """Send one image + prompt to local Ollama and return text output."""
    # Read image bytes and base64-encode for the API payload.
    with open(image_file_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # Build the request body (Ollama chat format).
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

    # Send image + prompt to local Ollama VLM.
    response = requests.post(f"{ollama_host}/api/chat", json=body, timeout=600)
    response.raise_for_status()
    result = response.json()
    return result["message"]["content"]


# 1. START SERVER (IF NEEDED) #########################

start_ollama_server()

# 2. LOCAL VLM QUERY #################################

# Make sure the downscaled image exists before we send it.
if not os.path.exists(image_path_small):
    raise FileNotFoundError(f"Image not found: {image_path_small}")

resp = query_local(image_path_small, prompt, model)
print("\nVLM Response (local):")
print(resp)
