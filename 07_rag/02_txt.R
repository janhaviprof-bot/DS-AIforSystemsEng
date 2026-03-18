# 02_txt.R
# Example RAG workflow using a text file

# Load libraries
# install.packages(c("dplyr", "httr2", "jsonlite", "ollamar"), repos = c(CRAN = "https://packagemanager.posit.co/cran/latest"))
library(dplyr) # for data wrangling
library(httr2) # for HTTP requests
library(jsonlite) # for JSON operations
library(ollamar) # for interacting with the LLM
source("07_rag/functions.R")

MODEL = "smollm2:1.7b" # use this small model
PORT = 11434 # use this default port
OLLAMA_HOST = paste0("http://localhost:", PORT) # use this default host
DOCUMENT = "07_rag/data/sample.txt" # path to the text document to search

# Define a search function for text files
search_text = function(query, document_path) {
    # Read the text file
    text_content = readLines(document_path, warn = FALSE)
    
    # Find lines containing the query (case-insensitive)
    matching_lines = grep(query, text_content, ignore.case = TRUE, value = TRUE)
    if(length(matching_lines) == 0){ matching_lines = character(0) }
    # Combine matching lines into a single text
    result_text = paste(matching_lines, collapse = "\n")

    # Return as a simple list structure that can be converted to JSON
    result = list(
        query = query,
        document = basename(document_path),
        matching_content = result_text,
        num_lines = length(matching_lines)
    )
    return(result)
}

# Test search function
search_text("supervised", DOCUMENT)

# Example: Search for content about a specific topic
input = list(topic = "supervised learning")

# Task 1: Data Retrieval - Search the text document for relevant content
result1 = search_text(input$topic, DOCUMENT)

# Convert results to JSON for the LLM
result1_json = result1 %>%
    jsonlite::toJSON(auto_unbox = TRUE)

# Task 2: Generation augmented with the retrieved data
# Generate an explanation based on the retrieved content
role = "Output a clear explanation of the topic based on the retrieved content. Format as markdown with a title and well-structured paragraphs. If the content is incomplete, note that in your response."

# Using our custom agent_run function, which wraps ollamar::chat
result2 = agent_run(
    role = role, 
    task = result1_json, 
    model = MODEL, 
    output = "text"
)

# View result
cat(result2)

# Alternative: Manual chat approach, using ollamar::chat
result2b = chat(
    model = MODEL,
    messages = list(
        list(role = "system", content = role),
        list(role = "user", content = result1_json)
    ), 
    output = "text", 
    stream = FALSE
)

# View result
cat(result2b)
