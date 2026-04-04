# functions.py
# Function Calling Helper Functions
# Pairs with functions.R
# Tim Fraser

# This script contains functions used for multi-agent orchestration with function calling in Python.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import requests  # for HTTP requests
import json      # for working with JSON
import pandas as pd  # for data manipulation
import sys       # for stack frame inspection
import time      # for simple polling/retry

# If you haven't already, install these packages...
# pip install requests pandas

## 0.2 Configuration #################################

# Default model and Ollama connection
DEFAULT_MODEL = "smollm2:1.7b"
PORT = 11434
OLLAMA_HOST = f"http://localhost:{PORT}"
CHAT_URL = f"{OLLAMA_HOST}/api/chat"
REQUEST_TIMEOUT = 300  # seconds; avoid hanging indefinitely on network/model issues
OLLAMA_TAGS_URL = f"{OLLAMA_HOST}/api/tags"


def ensure_ollama_available(max_wait_seconds: int = 15, poll_interval_seconds: float = 0.5) -> None:
    """
    Fail fast with a helpful message if Ollama isn't reachable.
    """
    deadline = time.time() + max_wait_seconds
    last_err = None
    while time.time() < deadline:
        try:
            r = requests.get(OLLAMA_TAGS_URL, timeout=5)
            if r.ok:
                return
        except Exception as e:
            last_err = e
        time.sleep(poll_interval_seconds)

    raise RuntimeError(
        "Ollama is not reachable at localhost:11434. "
        "Start it first with: `python 08_function_calling/01_ollama.py`.\n"
        f"Last error: {last_err}"
    )

## 0.3 Tool implementations (agent resolves names in this module) #################################

def average_array(numbers):
    """Return the arithmetic mean of a list of numbers."""
    if len(numbers) == 0:
        return None
    return sum(numbers) / len(numbers)

# 1. AGENT FUNCTION ###################################

def agent(messages, model=DEFAULT_MODEL, output="text", tools=None, all=False):
    """
    Agent wrapper function that runs a single agent, with or without tools.
    
    Parameters:
    -----------
    messages : list
        List of message dictionaries with 'role' and 'content' keys.
        Must follow format: [{"role": "system", "content": "..."}, ...]
    model : str
        The model to be used for the agent (default: "smollm2:1.7b")
    output : str
        The output format (default: "text")
    tools : list, optional
        List of tool metadata dictionaries for function calling
    all : bool
        If True, return all responses. If False, return only the last response.
    
    Returns:
    --------
    str or list
        The agent's response(s)
    """
    
    # If the agent has NO tools, perform a standard chat
    if tools is None:
        ensure_ollama_available()
        body = {
            "model": model,
            "messages": messages,
            "stream": False,
            # Token cap makes runtime more predictable for students' machines.
            "options": {"num_predict": 500},
        }
        
        response = requests.post(CHAT_URL, json=body, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        
        return result["message"]["content"]
    else:
        # If the agent has tools, perform a tool call
        ensure_ollama_available()
        body = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "options": {"num_predict": 500},
        }
        
        response = requests.post(CHAT_URL, json=body, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        
        # For any given tool call, execute the tool call
        if "tool_calls" in result.get("message", {}):
            tool_calls = result["message"]["tool_calls"]
            for tool_call in tool_calls:
                # Execute the tool function
                # Note: Tool functions must be defined in the global scope
                func_name = tool_call["function"]["name"]
                raw_args = tool_call["function"].get("arguments", {})
                # Ollama may return tool arguments either as a JSON string or as an already-parsed dict.
                # Keep behavior consistent with the R examples (where arguments are already structured).
                func_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                
                # Get the function from globals and execute it
                func = globals().get(func_name)
                # `agent()` lives in this module, but students typically define tool functions
                # in the *calling script* (e.g. `03_agents_with_function_calling.py`).
                # Search up the stack to find the function in caller globals.
                if func is None:
                    for depth in range(1, 6):  # reasonable small bound for examples
                        try:
                            frame = sys._getframe(depth)
                            func = frame.f_globals.get(func_name)
                            if func is not None:
                                break
                        except ValueError:
                            break
                if func:
                    tool_output = func(**func_args)
                    tool_call["output"] = tool_output
        
        if all:
            return result
        else:
            # When output="tools", return the tool_calls list with outputs
            # When output="text", return the last tool call output or message content
            if "tool_calls" in result.get("message", {}):
                if output == "tools":
                    return tool_calls
                else:
                    return tool_calls[-1].get("output", result["message"]["content"])
            return result["message"]["content"]


def agent_run(role, task, tools=None, output="text", model=DEFAULT_MODEL):
    """
    Run an agent with a specific role and task.
    
    Parameters:
    -----------
    role : str
        The system prompt defining the agent's role
    task : str
        The user message/task for the agent
    tools : list, optional
        List of tool metadata for function calling
    output : str
        Output format (default: "text")
    model : str
        Model to use (default: DEFAULT_MODEL)
    
    Returns:
    --------
    str
        The agent's response
    """
    
    # Define the messages to be sent to the agent
    messages = [
        {"role": "system", "content": role},
        {"role": "user", "content": task}
    ]
    
    # Run the agent
    resp = agent(messages=messages, model=model, output=output, tools=tools)
    return resp


# 2. DATA CONVERSION FUNCTION ###################################

def df_as_text(df):
    """
    Convert a pandas DataFrame to a markdown table string.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        The DataFrame to convert to text
    
    Returns:
    --------
    str
        A markdown-formatted table string
    """
    
    # Convert DataFrame to markdown table
    # pandas to_markdown() method creates markdown tables
    tab = df.to_markdown(index=False)
    return tab
