# 03_agents_with_function_calling.py
# Agents with Function Calling
# Pairs with 03_agents_with_function_calling.R
# Tim Fraser

# This script demonstrates how to build agents that can use function calling.
# Students will learn how to create agent wrapper functions and use multiple tools.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import requests  # for HTTP requests
import json      # for working with JSON
import pandas as pd  # for data manipulation

# If you haven't already, install these packages...
# pip install requests pandas

## 0.2 Load Functions #################################

# Load helper functions for agent orchestration
from functions import agent

## 0.3 Configuration #################################

# Select model of interest
MODEL = "smollm2:1.7b"

# 1. DEFINE FUNCTIONS TO BE USED AS TOOLS ###################################

# Define a function to be used as a tool
def add_two_numbers(x, y):
    """Add two numbers together."""
    return x + y

# Define another function to be used as a tool
def get_table(df=None):
    """
    Convert a pandas DataFrame into a markdown table.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        The DataFrame to convert to a markdown table
    
    Returns:
    --------
    str
        Markdown-formatted table string
    """
    # Tool-call arguments arrive as JSON-ish structures; coerce them to a DataFrame.
    # This keeps the example working even when the model passes `df` as a dict or list.
    if df is None:
        df = pd.DataFrame()
    elif isinstance(df, str):
        # Ollama sometimes passes nested JSON as a string; try to parse it.
        try:
            df = json.loads(df)
        except Exception:
            pass
    if hasattr(df, "to_markdown"):
        return df.to_markdown(index=False)
    if isinstance(df, dict):
        df = pd.DataFrame(df)
    elif isinstance(df, list):
        df = pd.DataFrame(df)
    else:
        df = pd.DataFrame([df])
    return df.to_markdown(index=False)

# 2. DEFINE TOOL METADATA ###################################

# Define the tool metadata for add_two_numbers
tool_add_two_numbers = {
    "type": "function",
    "function": {
        "name": "add_two_numbers",
        "description": "Add two numbers",
        "parameters": {
            "type": "object",
            "required": ["x", "y"],
            "properties": {
                "x": {
                    "type": "number",
                    "description": "first number"
                },
                "y": {
                    "type": "number",
                    "description": "second number"
                }
            }
        }
    }
}

# Define the tool metadata for get_table
tool_get_table = {
    "type": "function",
    "function": {
        "name": "get_table",
        "description": "Convert a data.frame into a markdown table",
        "parameters": {
            "type": "object",
            "required": [],
            "properties": {
                "df": {
                    "type": "object",
                    "description": "The data.frame to convert to a markdown table using pandas to_markdown()"
                }
            }
        }
    }
}

# 3. EXAMPLE 1: STANDARD CHAT (NO TOOLS) ###################################

# Trying to call a standard chat without tools
# The agent() function from functions.py handles this automatically
messages = [
    {"role": "user", "content": "Write a haiku about cheese."}
]

resp = agent(messages=messages, model=MODEL, output="text")
print("Standard Chat Response:")
print(resp)
print()

# 4. EXAMPLE 2: TOOL CALL #1 ###################################

# Try calling tool #1 (add_two_numbers)
messages = [
    {"role": "user", "content": "Add 3 + 5."}
]

resp = agent(messages=messages, model=MODEL, output="tools", tools=[tool_add_two_numbers])
print("Tool Call #1 Result:")
print(resp)
print()

# Access the output from the tool call
if isinstance(resp, list) and len(resp) > 0:
    print(f"Tool output: {resp[0].get('output', 'No output')}")
    print()

# 5. EXAMPLE 3: TOOL CALL #2 ###################################

# Try calling tool #2 (get_table)
# First, create a simple DataFrame with the result from tool #1
result_value = resp[0].get("output", 0) if isinstance(resp, list) else 0
df = pd.DataFrame({"x": [result_value]})

messages = [
    {
        "role": "user",
        "content": (
            f"Call the tool get_table with df equal to this JSON object: {{\"x\": [{result_value}]}}. "
            f"Return only the tool call."
        ),
    }
]

resp2 = agent(messages=messages, model=MODEL, output="tools", tools=[tool_get_table])
print("Tool Call #2 Result:")
print(resp2)
print()

# Compare against manual approach
print("Manual Table Creation:")
manual_table = df.to_markdown(index=False)
print(manual_table)
print()

# Note: We can use the agent() function to rapidly build and test out agents with or without tools.
