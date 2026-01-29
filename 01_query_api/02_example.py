# 02_example_python.py
# Simple example of making an API request in Python
# Pairs with 02_example.R
# Tim Fraser

# This script shows how to:
# - Load an API key from a .env file
# - Make a GET request to an example API
# - Inspect the HTTP status code and JSON response

# 0. Setup #################################

## 0.1 Load Packages ############################

# !pip install requests python-dotenv  # run this once in your environment

import os  # for reading environment variables
import requests  # for making HTTP requests
from dotenv import load_dotenv  # for loading variables from .env

## 0.2 Load Environment Variables ################

# Load environment variables from the .env file in the project root
# This matches the behavior of readRenviron(".env") in 02_example.R
load_dotenv(".env")

# Get the API key from the environment
TEST_API_KEY = os.getenv("TEST_API_KEY")

## 1. Make API Request ###########################

# Execute query and save response as object
response = requests.get(
    "https://reqres.in/api/users/2",
    headers={"x-api-key": TEST_API_KEY},
)

## 2. Inspect Response ###########################

# View response status code (200 = success)
print(response.status_code)

# Extract the response as JSON and print
print(response.json())


# Clear environment (optional in short scripts, but shown for parity
# with the R example that clears its workspace)
globals().clear()