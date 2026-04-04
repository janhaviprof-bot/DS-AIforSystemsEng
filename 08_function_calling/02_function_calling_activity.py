# 02_function_calling_activity.py
# Basic Function Calling Example (activity)
# Pairs with 02_function_calling.R
# Tim Fraser

# This script demonstrates how to use function calling with an LLM in Python.
# With several tools registered, the model picks the one that matches the user question.

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

def multiply_two_numbers(x, y):
    """
    Multiply two numbers together.
    
    Parameters:
    -----------
    x : float
        First number
    y : float
        Second number
    
    Returns:
    --------
    float
        Multiplication of x and y
    """
    return x * y

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

tool_multiply_two_numbers = {
    "type": "function",
    "function": {
        "name": "multiply_two_numbers",
        "description": "Multiply two numbers",
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

# Shared tool list when you want the model to choose add vs multiply
BOTH_TOOLS = [tool_add_two_numbers, tool_multiply_two_numbers]


def chat_with_tools(messages, tools, label):
    """Send one chat request and run any tool_calls Ollama returns."""
    body = {"model": MODEL, "messages": messages, "tools": tools, "stream": False}
    response = requests.post(CHAT_URL, json=body)
    response.raise_for_status()
    result = response.json()
    print(label)
    msg = result.get("message", {})
    if "tool_calls" not in msg:
        # Common when the question does not match the only tool offered (e.g. "3+2" with multiply only)
        print("No tool calls in response")
        if msg.get("content"):
            print(f"Model text instead: {msg['content']}")
        return
    for tool_call in msg["tool_calls"]:
        func_name = tool_call["function"]["name"]
        raw_args = tool_call["function"]["arguments"]
        func_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        func = globals().get(func_name)
        if func:
            output = func(**func_args)
            print(f"  Called {func_name} -> {output}")
            tool_call["output"] = output
        else:
            print(f"  No Python function named {func_name} in this script")
    print()


# 3. CREATE CHAT REQUEST WITH TOOLS ###################################

# Example A: addition wording — model should choose add_two_numbers (not multiply)
chat_with_tools(
    messages=[{"role": "user", "content": "What is 3 + 2?"}],
    tools=BOTH_TOOLS,
    label="Example A (both tools, addition question):",
)

# Example B: multiplication wording — model should choose multiply_two_numbers
chat_with_tools(
    messages=[{"role": "user", "content": "What is 3 times 2?"}],
    tools=BOTH_TOOLS,
    label="Example B (both tools, multiplication question):",
)
