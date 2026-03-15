# 03_agents.py
# Multi-Agent Workflow
# Pairs with 03_agents.R
# Tim Fraser

# This script demonstrates how to build a set of agents to query data,
# perform analysis, and interpret it. Students will learn multi-agent orchestration.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import pandas as pd  # for data manipulation
import requests      # for HTTP requests
import os
from pathlib import Path

# If you haven't already, install these packages...
# pip install pandas requests

# Set working directory to this script's folder.
# This makes relative imports and file paths consistent.
os.chdir("C:/Users/tmf77/courses/SYSEN5381/dsai/06_agents")

## 0.2 Load Functions #################################

# Load helper functions for agent orchestration
from functions import agent_run, get_shortages, df_as_text

# 1. CONFIGURATION ###################################

# Select model of interest
MODEL = "smollm2:135m"

# We will use the FDA Drug Shortages API to get data on drug shortages.
# https://open.fda.gov/apis/drug/drugshortages/

# Context the tool needs to know
categories = [
    "Analgesia/Addiction", "Anesthesia", "Anti-Infective", "Antiviral",
    "Cardiovascular", "Dental", "Dermatology", "Endocrinology/Metabolism",
    "Gastroenterology", "Hematology", "Inborn Errors", "Medical Imaging",
    "Musculoskeletal", "Neurology", "Oncology", "Ophthalmology", "Other",
    "Pediatric", "Psychiatry", "Pulmonary/Allergy", "Renal", "Reproductive",
    "Rheumatology", "Total Parenteral Nutrition", "Transplant", "Urology"
]

# 2. WORKFLOW EXECUTION ###################################

# Start with an input type of medication to search
input_category = {"category": "Psychiatry"}

# Task 1 - Function -------------------------
# Get data on drug shortages for the category of interest
data = get_shortages(category=input_category["category"], limit=500)


# Process the data into some summary table
# Filter for items that are currently unavailable


stat = data.groupby("generic_name").apply(lambda x: x.loc[x["update_date"].idxmax()])
# stat = (data
#         .groupby("generic_name")
#         .apply(lambda x: x.loc[x["update_date"].idxmax()])
#         .reset_index(drop=True)
#         .query("availability == 'Unavailable'"))

# data

# NOTE: The API data in 'data' chang
# es over time,
# so sometimes if you filter to availability == "Unavailable",
# there literally may be no rows with that trait.
# If that's the case, the 'stat' table will be empty.
# Just remove the line `.query("availability" == "Unavailable")` if that's the case.


# Convert the data to a text string
#You dont need to convert in markdown to save token you can save it seperated by comma.
task2 = df_as_text(stat)

# Task 2 - Analyst Agent -------------------------
# This agent analyzes the data and returns a markdown table
role2 = "I analyze medicine shortage data provided by the user in a table, and return a markdown table of currently ongoing shortages."
result2 = agent_run(role=role2, task=task2, model=MODEL, output="text")

result2

# Task 3 - Press Release Agent -------------------------
# This agent takes the analysis and writes a press release
role3 = "I write a 1-page press release on the currently ongoing shortages, 
using the analysis provided by the user."
result3 = agent_run(role=role3, task=result2, model=MODEL, output="text")
result3

# 3. VIEW RESULTS ###################################

# View press release
print("📰 Press Release:")
print(result3)
