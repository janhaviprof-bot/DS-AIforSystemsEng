# test_requests.py
# POST Request with JSON Data
# Pairs with ACTIVITY_add_documentation_to_cursor.md
# Tim Fraser

# This script demonstrates how to make a POST request with JSON data
# using the Python requests library. httpbin.org echoes back the request for testing.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import requests

# 1. SEND REQUEST ###################################

# Make a POST request with JSON data
# The json= parameter serializes the dict to JSON and sets Content-Type header
url = "https://httpbin.org/post"
data = {"name": "test"}
response = requests.post(url, json=data)

# 2. PARSE RESPONSE ################################

# Get the response
print(response.status_code)
print(response.json())
