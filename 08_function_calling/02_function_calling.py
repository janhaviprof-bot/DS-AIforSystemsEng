# 02_function_calling.py
# Basic Function Calling Example
# Pairs with 02_function_calling.R
# Tim Fraser

# This script demonstrates how to use function calling with an LLM in Python.
# Students will learn how to define functions as tools and execute tool calls.

# Further reading: https://docs.ollama.com/function-calling

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import requests  # for HTTP requests
import json      # for working with JSON

# If you haven't already, install the requests package...
# pip install requests

## 0.2 Configuration #################################

# Select model of interest
# Note: Function calling requires a model that supports tools (e.g., smollm2:1.7b)
MODEL = "smollm2:1.7b"

# Set the port where Ollama is running
PORT = 11434
OLLAMA_HOST = f"http://localhost:{PORT}"
CHAT_URL = f"{OLLAMA_HOST}/api/chat"

# 1. DEFINE A FUNCTION TO BE USED AS A TOOL ###################################

# Define a function to be used as a tool
# This function must be defined in the global scope so it can be called
def add_two_numbers(x, y):
    """
    Add two numbers together.
    
    Parameters:
    -----------
    x : float
        First number
    y : float
        Second number
    
    Returns:
    --------
    float
        Sum of x and y
    """
    return x + y

# 2. DEFINE TOOL METADATA ###################################

# Define the tool metadata as a dictionary
# This tells the LLM what the function does and what parameters it needs
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

# 3. CREATE CHAT REQUEST WITH TOOLS ###################################
# Create a simple chat history with a user question that will require the tool
messages = [
    {"role": "user", "content": "What is 3 + 2?"}
]

# Build the request body with tools
body = {
    "model": MODEL,
    "messages": messages,
    "tools": [tool_add_two_numbers],
    "stream": False
}

# Send the request
response = requests.post(CHAT_URL, json=body)
response.raise_for_status()
result = response.json()


# 4. EXECUTE THE TOOL CALL ###################################

# Receive back the tool call
# The LLM will return a tool_calls array with the function name and arguments
if "tool_calls" in result.get("message", {}):
    tool_calls = result["message"]["tool_calls"]
    
    # Execute each tool call
    for tool_call in tool_calls:
        func_name = tool_call["function"]["name"]
        # Ollama may return arguments as a JSON string or an already-parsed dict
        raw_args = tool_call["function"]["arguments"]
        func_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        
        # Get the function from globals and execute it
        func = globals().get(func_name)
        if func:
            output = func(**func_args)
            print(f"Tool call result: {output}")
            tool_call["output"] = output
else:
    print("No tool calls in response")
