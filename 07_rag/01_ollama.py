# 01_ollama.py
# Launch Ollama from Python
# Pairs with 01_ollama.sh / 01_ollama.R
# Tim Fraser (Python adaptation)

# This script configures environment variables for Ollama,
# then starts `ollama serve` in the background without blocking
# the Python session. Useful for starting a local LLM server
# from within Python notebooks or scripts.

import os
import subprocess
import time

# 0. Setup #################################

## 0.1 Configuration ############################

PORT = 11434  # Match 01_ollama.sh
OLLAMA_HOST = f"0.0.0.0:{PORT}"
OLLAMA_CONTEXT_LENGTH = 32000

# Set environment variables for this process and any child processes
os.environ["OLLAMA_HOST"] = OLLAMA_HOST
os.environ["OLLAMA_CONTEXT_LENGTH"] = str(OLLAMA_CONTEXT_LENGTH)

## 0.2 Start Ollama Server #######################

# Start `ollama serve` in the background.
# stdout/stderr are redirected to DEVNULL so the console is not flooded.
process = subprocess.Popen(
    ["ollama", "serve"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

# Give the server a moment to start listening before use
time.sleep(1)

# Optional: you can keep a reference to `process` if you want to stop it later
# For example:
# process.terminate()  # or process.kill()

# On Windows, from a separate shell you can also stop it with:
#   taskkill /F /IM ollama.exe