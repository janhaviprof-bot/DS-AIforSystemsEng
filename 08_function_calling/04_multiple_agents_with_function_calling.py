# 04_multiple_agents_with_function_calling.py
# Multiple Agents with Function Calling
# Pairs with 04_multiple_agents_with_function_calling.R
# Tim Fraser

# This script demonstrates how to build a graph of agents and their interactions,
# using function calling to query data, perform analysis, and interpret it.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import requests  # for HTTP requests
import json      # for working with JSON
import pandas as pd  # for data manipulation
from datetime import datetime  # for date parsing

# If you haven't already, install these packages...
# pip install requests pandas

## 0.2 Load Functions #################################

# Load helper functions for agent orchestration
from functions import agent_run, df_as_text

## 0.3 Configuration #################################

# Select model of interest
MODEL = "smollm2:1.7b"

# We will use the FDA Drug Shortages API to get data on drug shortages.
# https://open.fda.gov/apis/drug/drugshortages/

# 1. DEFINE API FUNCTION AS A TOOL ###################################

def get_shortages(category="Psychiatry", limit=500):
    """
    Get data on drug shortages from the FDA Drug Shortages API.
    
    Parameters:
    -----------
    category : str
        The therapeutic category of the drug (default: "Psychiatry")
    limit : int
        The maximum number of results to return (default: 500)
    
    Returns:
    --------
    pandas.DataFrame
        A DataFrame of drug shortages
    """
    
    # FDA Drug Shortages API endpoint
    url = "https://api.fda.gov/drug/shortages.json"
    
    # Build query parameters
    params = {
        "sort": "initial_posting_date:desc",
        "search": f'dosage_form:"Capsule"+status:"Current"+therapeutic_category:"{category}"',
        "limit": limit
    }
    
    # Perform the request
    response = requests.get(
        url,
        params=params,
        headers={"Accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    
    # Parse the response as JSON
    data = response.json()
    
    # Process the data into a pandas DataFrame
    results = data.get("results", [])
    
    # Extract relevant fields
    processed_data = []
    for item in results:
        processed_data.append({
            "generic_name": item.get("generic_name", ""),
            "update_type": item.get("update_type", ""),
            "update_date": item.get("update_date", ""),
            "availability": item.get("availability", ""),
            "related_info": item.get("related_info", "")
        })
    
    # Convert to DataFrame
    df = pd.DataFrame(processed_data)
    
    # Parse dates (FDA API uses M/D/YYYY format)
    if not df.empty and "update_date" in df.columns:
        df["update_date"] = pd.to_datetime(df["update_date"], format="%m/%d/%Y", errors="coerce")
    
    return df

# 2. DEFINE TOOL METADATA ###################################

# Context the tool needs to know
categories = [
    "Analgesia/Addiction", "Anesthesia", "Anti-Infective", "Antiviral",
    "Cardiovascular", "Dental", "Dermatology", "Endocrinology/Metabolism",
    "Gastroenterology", "Hematology", "Inborn Errors", "Medical Imaging",
    "Musculoskeletal", "Neurology", "Oncology", "Ophthalmology", "Other",
    "Pediatric", "Psychiatry", "Pulmonary/Allergy", "Renal", "Reproductive",
    "Rheumatology", "Total Parenteral Nutrition", "Transplant", "Urology"
]

# Define the tool metadata as a dictionary
tool_get_shortages = {
    "type": "function",
    "function": {
        "name": "get_shortages",
        "description": "Get data on drug shortages",
        "parameters": {
            "type": "object",
            "required": ["category", "limit"],
            "properties": {
                "category": {
                    "type": "string",
                    "description": "the therapeutic category of the drug (e.g., Psychiatry)"
                },
                "limit": {
                    "type": "number",
                    "description": "the max number of results to return. Default is 500."
                }
            }
        }
    }
}

# 3. MULTI-AGENT WORKFLOW ###################################

# Let's create an agentic workflow with function calling.

# Agent 1: Data Fetcher (with tools)
# This agent uses the get_shortages tool to fetch data from the API
task = "Get data on drug shortages for the category Psychiatry with limit 10"
role1 = "I fetch information from the FDA Drug Shortages API"
result1_calls = agent_run(role=role1, task=task, model=MODEL, output="tools", tools=[tool_get_shortages])

# When output="tools", agent_run() returns a list of tool_calls.
# The actual tool output is stored at tool_call["output"].
result1_df = (
    result1_calls[0].get("output")
    if isinstance(result1_calls, list) and len(result1_calls) > 0
    else None
)

# Convert it to text for the next agent (keep prompt small)
result1_text = df_as_text(result1_df.head(10))

# Agent 2: Data Analyst (no tools)
# This agent analyzes the data and returns a markdown table
role2 = "I analyze data in a table format and return a markdown table of currently ongoing shortages."
result2 = agent_run(role=role2, task=result1_text, model=MODEL, output="text", tools=None)

# Agent 3: Press Release Writer (no tools)
# This agent writes a press release based on the analysis
role3 = "I write a 1-page press release on the currently ongoing shortages."
result3 = agent_run(role=role3, task=result2, model=MODEL, output="text", tools=None)

# 4. VIEW RESULTS ###################################

print("Agent 1 Result (Data Fetch):")
print(f"Retrieved {len(result1_df)} records")
print(result1_df.head())
print()

print("Agent 2 Result (Analysis):")
print(result2)
print()

print("Agent 3 Result (Press Release):")
print(result3)
