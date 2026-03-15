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

# If you haven't already, install these packages...
# pip install pandas requests

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
stat = (data
        .groupby("generic_name")
        .apply(lambda x: x.loc[x["update_date"].idxmax()])
        .reset_index(drop=True)
        .query("availability == 'Unavailable'"))

# Convert the data to a text string
#You dont need to convert in markdown to save token you can save it seperated by comma.
task2 = df_as_text(stat)

# Task 2 - Analyst Agent -------------------------
# This agent analyzes the data and returns a markdown table
role2 = "I analyze medicine shortage data provide by the user in a table, and return a markdown table of currently ongoing shortages."
result2 = agent_run(role=role2, task=task2, model=MODEL, output="text")

# Task 3 - Press Release Agent -------------------------
# This agent takes the analysis and writes a press release
role3 = "I write a 1-page press release on the currently ongoing shortages, using the analysis provided by the user."
result3 = agent_run(role=role3, task=result2, model=MODEL, output="text")

# 3. VIEW RESULTS ###################################

# View press release
print("📰 Press Release:")
print(result3)
