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
os.chdir(Path(__file__).resolve().parent)

## 0.2 Load Functions #################################

# Load helper functions for agent orchestration
from functions import agent_run, get_shortages, df_as_text

# 1. CONFIGURATION ###################################

# Select model of interest
MODEL = "smollm2:1.7b"

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

# Task 1 - Function -------------------------
# Get data on drug shortages for all categories; keep current availability (latest per drug per category)
data_list = []
for cat in categories:
    df = get_shortages(category=cat, limit=500)
    df["category"] = cat
    data_list.append(df)
data = pd.concat(data_list, ignore_index=True)

# Process the data: latest record per drug per category (current availability)
stat = (
    data.groupby(["generic_name", "category"])
    .apply(lambda x: x.loc[x["update_date"].idxmax()])
    .reset_index(drop=True)
)
# Optional: filter to currently unavailable only (can make stat empty if API has none)
# stat = stat.query("availability == 'Unavailable'")


# Convert the data to a text string
#You dont need to convert in markdown to save token you can save it seperated by comma.
task2 = df_as_text(stat)

# Task 2 - Summary Agent -------------------------
# This agent analyzes the data and returns a markdown table
role2 = "I analyze medicine shortage data provided by the user in a table, and summarise the data in summary form ."
result2 = agent_run(role=role2, task=task2, model=MODEL, output="text")

# Task 3 - Finance Agent -------------------------
# This agent takes the summary and provides analysis and prediction
role3 = "I take the summary data of the available drugs and provide financial analysis on how it will affect the drug market."
result3 = agent_run(role=role3, task=result2, model=MODEL, output="text")

# 3. VIEW RESULTS ###################################

# View Final Analysis
print("📰 Market Analysis:")
print(result3)
