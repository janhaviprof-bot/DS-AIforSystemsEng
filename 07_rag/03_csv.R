# 03_csv.R
# Example RAG workflow using a CSV file

# Load libraries
# install.packages(c("dplyr", "readr", "httr2", "jsonlite", "ollamar"), repos = c(CRAN = "https://packagemanager.posit.co/cran/latest"))
library(dplyr) # for data wrangling
library(readr) # for reading CSV files
library(httr2) # for HTTP requests
library(jsonlite) # for JSON operations
library(ollamar) # for interacting with the LLM
source("07_rag/functions.R")

MODEL = "smollm2:1.7b" # use this small model
PORT = 11434 # use this default port
OLLAMA_HOST = paste0("http://localhost:", PORT) # use this default host
DOCUMENT = "07_rag/data/pokemon.csv" # path to the document to search

# Define a search function we will operate programmatically
search = function(query, document){
    read_csv(document, show_col_types = FALSE) %>%
        filter(stringr::str_detect(Name, query)) %>%
        as.list() %>%
        jsonlite::toJSON(auto_unbox = TRUE) 
}

# Test search function
search("Pikachu", DOCUMENT)


# Suppose the user supplies a specific item to search
input = list(pokemon = "Pikachu")

# Task 1: Data Retrieval - Search the document for the item
result1 = search(input$pokemon, DOCUMENT)

# Task 2: Generation augmented with the data retrieved
# Generate a profile description of the Pokemon
role = "Output a short 200 word profile description of the Pokemon using the data provided by the user, written in markdown. Include a title, tagline, and notable stats."

# Using our custom agent_run function, which wraps ollamar::chat
result2 = agent_run(role = role, task = result1, model = MODEL, output = "text")

# View result
cat(result2)

# Alternative: Manual chat approach, using ollamar::chat
result2b = chat(
    model = MODEL,
    messages = list(
        list(role = "system", content = role),
        list(role = "user", content = result1)
    ), 
    output = "text", 
    stream = FALSE
)

# View result
result2b

