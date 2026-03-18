# 02_txt.py
# Example RAG workflow using a text file
# Pairs with 02_txt.R
# Tim Fraser

# This script demonstrates how to perform Retrieval-Augmented Generation (RAG) with a text file.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import os        # for file path operations
import runpy     # for executing another Python script
import requests  # for HTTP requests
import json      # for working with JSON

## 0.2 Working Directory #################################

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__name__))
os.chdir(script_dir)

## 0.3 Start Ollama Server (source 01_ollama.py) #################################

# Execute 01_ollama.py as if we were sourcing it in R.
# This will configure environment variables and start `ollama serve` in the background.
ollama_script_path = os.path.join(os.getcwd(), "01_ollama.py")
_ = runpy.run_path(ollama_script_path)


## 0.4 Load Functions #################################

# Load helper functions for agent orchestration
from functions import agent_run

## 0.3 Configuration #################################

# Select model of interest
MODEL = "smollm2:1.7b"  # use this small model
PORT = 11434  # use this default port
OLLAMA_HOST = f"http://localhost:{PORT}"  # use this default host
DOCUMENT = "data/sample.txt"  # path to the text document to search

# 1. SEARCH FUNCTION ###################################

def search_text(query, document_path):
    """
    Search a text file for lines containing the query.
    
    Parameters:
    -----------
    query : str
        The search term to look for
    document_path : str
        Path to the text file to search
    
    Returns:
    --------
    dict
        Dictionary with query, document name, matching content, and line count
    """
    
    # Read the text file
    with open(document_path, 'r', encoding='utf-8') as f:
        text_content = f.readlines()
    
    # Find lines containing the query (case-insensitive)
    matching_lines = [line for line in text_content if query.lower() in line.lower()]
    
    if len(matching_lines) == 0:
        matching_lines = []
    
    # Combine matching lines into a single text
    result_text = "\n".join(matching_lines)
    
    # Return as a simple dictionary structure that can be converted to JSON
    result = {
        "query": query,
        "document": os.path.basename(document_path),
        "matching_content": result_text,
        "num_lines": len(matching_lines)
    }
    
    return result

# 2. TEST SEARCH FUNCTION ###################################

# Test search function
print("Testing search function...")
test_result = search_text("supervised", DOCUMENT)
print(f"Found {test_result['num_lines']} matching lines")
print(test_result)

# 3. RAG WORKFLOW ###################################

# Example: Search for content about a specific topic
input_data = {"topic": "supervised learning"}

# Task 1: Data Retrieval - Search the text document for relevant content
result1 = search_text(input_data["topic"], DOCUMENT)

# Convert results to JSON for the LLM
result1_json = json.dumps(result1, indent=2)

# Task 2: Generation augmented with the retrieved data
# Generate an explanation based on the retrieved content
role = "Output a clear explanation of the topic based on the retrieved content. Format as markdown with a title and well-structured paragraphs. If the content is incomplete, note that in your response."

# Using our custom agent_run function, which wraps requests.post
result2 = agent_run(
    role=role,
    task=result1_json,
    model=MODEL,
    output="text"
)

# View result
print("📝 Generated Explanation:")
print(result2)

# 4. ALTERNATIVE: MANUAL CHAT APPROACH ###################################

# Alternative: Manual chat approach, using requests.post directly
CHAT_URL = f"{OLLAMA_HOST}/api/chat"

messages = [
    {"role": "system", "content": role},
    {"role": "user", "content": result1_json}
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
