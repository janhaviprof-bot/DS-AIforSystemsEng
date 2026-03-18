# 03_csv.py
# Example RAG workflow using a CSV file
# Pairs with 03_csv.R
# Tim Fraser

# This script demonstrates how to perform Retrieval-Augmented Generation (RAG) with a CSV file.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import os        # for file path operations
import runpy     # for executing another Python script
import pandas as pd  # for reading CSV files and data manipulation
import requests      # for HTTP requests
import json          # for working with JSON

# 0.2 Working Directory #################################

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__name__))
os.chdir(script_dir)

## 0.3 Start Ollama Server (source 01_ollama.py) #################################

# Execute 01_ollama.py as if we were sourcing it in R.
# This will configure environment variables and start `ollama serve` in the background.
ollama_script_path = os.path.join(os.getcwd(), "01_ollama.py")
_ = runpy.run_path(ollama_script_path)


## 0.2 Load Functions #################################

# Load helper functions for agent orchestration
from functions import agent_run

## 0.3 Configuration #################################

# Select model of interest
MODEL = "smollm2:1.7b"  # use this small model
PORT = 11434  # use this default port
OLLAMA_HOST = f"http://localhost:{PORT}"  # use this default host
DOCUMENT = "data/pokemon.csv"  # path to the document to search

# 1. SEARCH FUNCTION ###################################

def search(query, document):
    """
    Search a CSV file for rows matching the query in the Name column.
    
    Parameters:
    -----------
    query : str
        The search term to look for
    document : str
        Path to the CSV file to search
    
    Returns:
    --------
    str
        JSON string of matching rows
    """
    
    # Read the CSV file
    df = pd.read_csv(document)
    
    # Filter rows where Name contains the query (case-insensitive)
    filtered_df = df[df["Name"].str.contains(query, case=False, na=False)]
    
    # Convert to dictionary and then to JSON
    result_dict = filtered_df.to_dict(orient="records")
    
    # Convert to JSON string (auto-unbox equivalent: ensure single-item lists become values)
    result_json = json.dumps(result_dict, indent=2)
    
    return result_json

# 2. TEST SEARCH FUNCTION ###################################

# Test search function
print("Testing search function...")
test_result = search("Pikachu", DOCUMENT)
print("Search result preview:")
print(test_result[:200] + "..." if len(test_result) > 200 else test_result)
print()

# 3. RAG WORKFLOW ###################################

# Suppose the user supplies a specific item to search
input_data = {"pokemon": "Pikachu"}

# Task 1: Data Retrieval - Search the document for the item
result1 = search(input_data["pokemon"], DOCUMENT)

# Task 2: Generation augmented with the data retrieved
# Generate a profile description of the Pokemon
role = "Output a short 200 word profile description of the Pokemon using the data provided by the user, written in markdown. Include a title, tagline, and notable stats."

# Using our custom agent_run function, which wraps requests.post
result2 = agent_run(role=role, task=result1, model=MODEL, output="text")

# View result
print("📝 Generated Pokemon Profile:")
print(result2)
print()

# 4. ALTERNATIVE: MANUAL CHAT APPROACH ###################################

# Alternative: Manual chat approach, using requests.post directly
CHAT_URL = f"{OLLAMA_HOST}/api/chat"

messages = [
    {"role": "system", "content": role},
    {"role": "user", "content": result1}
]

body = {
    "model": MODEL,
    "messages": messages,
    "stream": False
}

response = requests.post(CHAT_URL, json=body)
response.raise_for_status()
response_data = response.json()

result2b = response_data["message"]["content"]

# View result
print("📝 Alternative Approach Result:")
print(result2b)
