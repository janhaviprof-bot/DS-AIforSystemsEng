# 03_agents.R

# Load packages
library(dplyr)
library(stringr)
library(httr2)
library(jsonlite)
library(ollamar)
library(purrr)
library(lubridate)

# Load functions
source("functions.R")

# In this script, we will build a set of agents
# to query data, perform analysis, and interpret it.

# We will use the FDA Drug Shortages API to get data on drug shortages.
# https://open.fda.gov/apis/drug/drugshortages/

# Select model of interest
MODEL = "smollm2:135m"

# We will use this function, defined in 06_agents/functions.R
# get_shortages

# Context the tool needs to know
categories = c(
  "Analgesia/Addiction",
  "Anesthesia",
  "Anti-Infective",   
  "Antiviral",
  "Cardiovascular",
  "Dental",
  "Dermatology",
  "Endocrinology/Metabolism",
  "Gastroenterology",
  "Hematology",
  "Inborn Errors",
  "Medical Imaging",
  "Musculoskeletal",
  "Neurology",
  "Oncology",
  "Ophthalmology",
  "Other",
  "Pediatric",
  "Psychiatry",
  "Pulmonary/Allergy",
  "Renal",
  "Reproductive",
  "Rheumatology",
  "Total Parenteral Nutrition",
  "Transplant",
  "Urology"
)


# Get data from an API
# data = get_shortages("Psychiatry")

# Start with an input type of medication to search
input = list(category = "Psychiatry")

# Task 1 - Function -------------------------
# Get data on drug shortages for the category of interest
data = get_shortages(category = input$category, limit = 500)
# Process the data into some summary table - eg. just the items that are currently unavailable
stat = data %>%
  group_by(generic_name) %>%
  filter(update_date == max(update_date)) %>%
  filter(availability == "Unavailable") %>%
  ungroup()

# NOTE: The API data in 'data' changes over time,
# so sometimes if you filter to availability == "Unavailable",
# there literally may be no rows with that trait.
# If that's the case, the 'stat' table will be empty.
# Just remove the line `filter(availability == "Unavailable")` if that's the case.

# Convert the data to a text string
task2 = df_as_text(stat)

# Task 2 - Analyst Agent -------------------------
role2 = "I analyze medicine shortage data provide by the user in a table, and return a markdown table of currently ongoing shortages."
result2 = agent_run(role =  role2, task = task2, model = MODEL, output = "text")

# Task 3 - Press Release Agent -------------------------
role3 = "I write a 1-page press release on the currently ongoing shortages, using the analysis provided by the user."
result3 = agent_run(role = role3, task = result2, model = MODEL, output = "text")

# View press release
result3
