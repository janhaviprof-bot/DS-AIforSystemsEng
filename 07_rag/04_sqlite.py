# 04_sqlite.py
# Example RAG workflow using SQLite database
# Pairs with 04_sqlite.R
# Tim Fraser

# This script demonstrates how to perform Retrieval-Augmented Generation (RAG) with a SQLite database.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import sqlite3  # for SQLite database operations (built-in)
import pandas as pd  # for data manipulation
import requests  # for HTTP requests
import json      # for working with JSON
import os        # for file path operations
import runpy     # for executing another Python script

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
DB_PATH = "data/papers.db"  # path to the SQLite database

# 1. DATABASE CONNECTION ###################################

# Connect to database
conn = sqlite3.connect(DB_PATH)


# 2. SEARCH FUNCTION ###################################

def search_documents(query, db_connection, limit=5):
    """
    Search the database for documents matching the query.
    
    Parameters:
    -----------
    query : str
        The search term to look for
    db_connection : sqlite3.Connection
        Database connection object
    limit : int
        Maximum number of results to return (default: 5)
    
    Returns:
    --------
    pandas.DataFrame
        DataFrame with matching documents
    """
    
    # Search in title, content, and tags
    sql_query = """
        SELECT id, title, content, category, author, tags
        FROM documents
        WHERE title LIKE ? 
           OR content LIKE ?
           OR tags LIKE ?
        LIMIT ?
    """
    
    search_pattern = f"%{query}%"
    
    # Execute query with parameters
    results = pd.read_sql_query(
        sql_query,
        db_connection,
        params=(search_pattern, search_pattern, search_pattern, limit)
    )
    
    return results

# 3. TEST SEARCH FUNCTION ###################################

# Test search function
print("Testing search function...")
test_result = search_documents("machine learning", conn)
print(f"Found {len(test_result)} matching documents")
print(test_result[["title", "category"]].head() if len(test_result) > 0 else "No results")
print()

# 4. RAG WORKFLOW ###################################

# Example: Search for documents about a specific topic
input_data = {"topic": "database"}

# Task 1: Data Retrieval - Search the database for relevant documents; limit to 3 results
result1 = search_documents(input_data["topic"], conn, limit=3)

# Convert results to JSON for the LLM
# Convert DataFrame to dictionary, then to JSON
result1_dict = result1.to_dict(orient="records")
result1_json = json.dumps(result1_dict, indent=2)

# Task 2: Generation augmented with the retrieved data
# Generate a summary of the retrieved documents
role = "Output a concise summary of the retrieved documents, highlighting key concepts and connections between them. Format as markdown with a title and bullet points."

# Using our custom agent_run function, which wraps requests.post
result2 = agent_run(
    role=role,
    task=result1_json,
    model=MODEL,
    output="text"
)

# View result
print("📝 Generated Summary:")
print(result2)
print()

# 5. ALTERNATIVE: MANUAL CHAT APPROACH ###################################

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

# 6. CLEANUP ###################################

# Close database connection
conn.close()
