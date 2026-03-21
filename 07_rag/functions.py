# functions.py
# RAG Helper Functions
# Pairs with functions.R
# Tim Fraser

# This script contains functions used for Retrieval-Augmented Generation (RAG) workflows in Python.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import requests  # for HTTP requests
import json      # for working with JSON
import pandas as pd  # for data manipulation

# If you haven't already, install these packages...
# pip install requests pandas

## 0.2 Configuration #################################

# Default model and Ollama connection
DEFAULT_MODEL = "smollm2:135m"
PORT = 11434
OLLAMA_HOST = f"http://localhost:{PORT}"
CHAT_URL = f"{OLLAMA_HOST}/api/chat"

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
        The model to be used for the agent (default: "smollm2:135m")
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
        body = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        response = requests.post(CHAT_URL, json=body)
        response.raise_for_status()
        result = response.json()
        
        return result["message"]["content"]
    else:
        # If the agent has tools, perform a tool call
        body = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False
        }
        
        response = requests.post(CHAT_URL, json=body)
        response.raise_for_status()
        result = response.json()
        
        # For any given tool call, execute the tool call
        if "tool_calls" in result.get("message", {}):
            tool_calls = result["message"]["tool_calls"]
            for tool_call in tool_calls:
                # Execute the tool function
                # Note: Tool functions must be defined in the global scope
                func_name = tool_call["function"]["name"]
                func_args = json.loads(tool_call["function"]["arguments"])
                
                # Get the function from globals and execute it
                func = globals().get(func_name)
                if func:
                    output = func(**func_args)
                    tool_call["output"] = output
        
        if all:
            return result
        else:
            # Return the last tool call output or the message content
            if "tool_calls" in result.get("message", {}):
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


# 2. AIRCRAFT CHUNKS FOR RAG ###################################

# Spec fields to include in aircraft chunks for semantic search (filter/sort queries)
AIRCRAFT_SPEC_FIELDS = [
    "manufacturer", "first_flight", "status", "range_km", "cruise_speed_kmh",
    "max_speed_kmh", "capacity_passengers", "crew", "length_m", "wingspan_m",
]


def get_aircraft_chunks(csv_path=None, include_specs=True):
    """
    Read aircraft.csv and build text chunks for RAG semantic search.
    Each chunk includes name, type, description, and optional spec fields
    (manufacturer, first_flight, status, range_km, etc.) so queries like
    "long range", "Airbus", "high capacity" match relevant aircraft.

    Parameters:
    -----------
    csv_path : str, optional
        Path to aircraft.csv. Default: data/aircraft.csv relative to script dir.
    include_specs : bool
        If True (default), append spec fields to each chunk for better search.

    Returns:
    --------
    list of str
        Text chunks, one per aircraft
    """
    import os
    import csv as csv_module

    if csv_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(script_dir, "data", "aircraft.csv")

    chunks = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv_module.DictReader(f)
        for row in reader:
            parts = [
                f"Aircraft: {row.get('name', '')}.",
                f"Type: {row.get('type', '')}.",
                f"{row.get('short_description', '')}",
            ]
            if include_specs:
                specs = []
                for field in AIRCRAFT_SPEC_FIELDS:
                    val = row.get(field, "").strip()
                    if val:
                        label = field.replace("_", " ").title()
                        specs.append(f"{label}: {val}")
                if specs:
                    parts.append(" ".join(specs))
            chunks.append(" ".join(parts).strip())

    return chunks


# 3. DATA CONVERSION FUNCTION ###################################

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
