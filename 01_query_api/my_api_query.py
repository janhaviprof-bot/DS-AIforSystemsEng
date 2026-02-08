import os  # for reading environment variables
import requests  # for making HTTP requests
from dotenv import load_dotenv  # for loading variables from .envload_dotenv(".env")

# Get the API key from the environment
TEST_API_KEY = os.getenv("TEST_API_KEY")

## 1. Make API Request ###########################

# Execute query and save response as object
response = requests.get(
    "https://api.carbonintensity.org.uk/intensity" #API key is not required for this API.
)

## 2. Inspect Response ###########################

# View response status code (200 = success)
print(response.status_code)

print(response.json())