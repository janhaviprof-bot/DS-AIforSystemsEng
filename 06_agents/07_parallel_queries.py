# 07_parallel_queries.py
# Send Parallel Queries to Ollama in Python
# Pairs with 07_parallel_queries.R
# Tim Fraser
#
# Can we send queries to multiple agents at once? Yes!
#
# This script shows how to run basic qualitative coding / content analysis
# very quickly with a local LLM. We'll send many requests in parallel, then
# clean the outputs into standardized labels we can analyze.

# If you haven't already, install these packages...
# pip install requests pandas

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import time  # for timing parallel requests
from concurrent.futures import ThreadPoolExecutor  # for parallel API calls

import pandas as pd  # for reading and sampling feedback data
import requests  # for HTTP requests

## 0.2 Read Data #################################

# Text to classify:
# Let's take a random sample of 10 pieces of feedback.
texts = pd.read_csv("06_agents/07_feedback.csv").sample(n=10, random_state=42)

# 1. CONCEPT ###################################

# Here's an example where we can do basic "qualitative coding"
# (also called content analysis) very quickly.
# Content analysis is the process of examining text and categorizing it
# into meaningful themes or labels.
#
# Sociologists, anthropologists, and market researchers have used this
# approach for decades to analyze interviews, focus groups, and reviews.
#
# You already do this informally in daily life:
# a friend describes a movie, and you mentally tag it as
# "they liked it" or "they didn't like it."
#
# If we provide an LLM with clear, standardized instructions,
# it can help us do this classification at scale.


def get_request(content, prompt, model):
    """Build URL + request body for a local Ollama chat call."""
    port = 11434
    ollama_host = f"http://localhost:{port}"
    url = f"{ollama_host}/api/chat"

    # We use /api/chat so we can send multiple messages
    # (system instructions + user content), not just one prompt.
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": content},
        ],
        "stream": False,
    }
    return url, body


def req_perform(content, prompt, model):
    """Send one POST request and return assistant text."""
    url, body = get_request(content=content, prompt=prompt, model=model)
    response = requests.post(url, json=body, timeout=120)
    response.raise_for_status()
    return response.json()["message"]["content"]


# Create a system prompt asking for JSON-style output
# with only the sentiment label.
prompt = (
    "Your only task/role is to evaluate the sentiment of product reviews provided by the user. "
    "Your response should simply be 'positive', 'negative', or 'other'. "
    "Do not include any other text in your response. "
    "Do not include any extra formatting like '```json' in your response. "
    "The JSON string should have the following format: "
    '{"sentiment":"<sentiment of the review>"}'
)

model = "smollm2:1.7b"

# 2. TEST ONE REQUEST ###################################

# Do one quick test request.
test_resp = req_perform(content="booo", prompt=prompt, model=model)
print("Test response:")
print(test_resp)
print()

# 3. SEND REQUESTS IN PARALLEL ##########################

feedback_list = texts["feedback"].astype(str).tolist()

# Send all requests in parallel and time the operation.
start_time = time.time()
with ThreadPoolExecutor(max_workers=min(10, len(feedback_list))) as executor:
    responses = list(executor.map(lambda text: req_perform(text, prompt, model), feedback_list))
elapsed = time.time() - start_time

print(f"Time taken to send {len(feedback_list)} requests: {elapsed:.2f} seconds")

# View the results.
print("Raw responses:")
print(responses)

# 4. CLEAN SENTIMENT LABELS ############################

# Usually there are a few formatting deviations,
# so we use string extraction to get clean labels.
# In regex pattern matching, "|" means OR.
sentiments = (
    pd.Series(responses, name="response")
    .str.lower()
    .str.extract(r"(positive|negative|other)", expand=False)
)
print(sentiments)