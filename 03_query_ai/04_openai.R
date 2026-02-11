# 04_openai.R

# Query OpenAI Models with API Key
# This script demonstrates how to query OpenAI's models
# using your API key stored in the .env file

# Starting message
cat("\n🚀 Querying OpenAI in R...\n")

# If you haven't already, install these packages...
# install.packages(c("httr2", "jsonlite"))

# Load libraries
library(httr2)    # For HTTP requests
library(jsonlite) # For working with JSON
library(purrr) # For mapping and extracting values from lists

# Load environment variables from .env file
# readRenviron() is a built-in R function that reads .env files
# No external package needed!
if (file.exists(".env")){  readRenviron(".env")  } else {  warning(".env file not found. Make sure it exists in the project root.") }

# Get API key from environment variable
OPENAI_API_KEY = Sys.getenv("OPENAI_API_KEY")

# Check if API key is set
if (OPENAI_API_KEY == "") { stop("OPENAI_API_KEY not found in .env file. Please set it up first.") }

# OpenAI API endpoint
url = "https://api.openai.com/v1/responses"

# Construct the request body as a list
body = list(
  model = "gpt-4o-mini",  # Low-cost model
  input = "Hello! Please respond with: Model is working."
)

# Build and send the POST request to OpenAI API
res = request(url) %>%
  req_headers(
    "Authorization" = paste0("Bearer ", OPENAI_API_KEY),
    "Content-Type" = "application/json"
  ) %>%
  req_body_json(body) %>%   # Attach the JSON body
  req_method("POST") %>%   # Set HTTP method
  req_perform()             # Execute the request

# Parse the response JSON
response = resp_body_json(res)

# Optional for longer queries...
# Wait for the response to finish (OpenAI returns right away, then we poll until done)
# while (response$status %in% c("created", "in_progress")) {
#   Sys.sleep(0.5)
#   get_res = request(paste0("https://api.openai.com/v1/responses/", response$id)) %>%
#     req_headers("Authorization" = paste0("Bearer ", OPENAI_API_KEY)) %>%
#     req_perform()
#   response = resp_body_json(get_res)
# }

# Extract the model's reply (text is inside output_items)
# or, grosser version:
output = response$output[[1]]$content[[1]]$text
# Or, using purrr package
response %>% purrr::pluck('output') %>% purrr::pluck(1) %>% purrr::pluck('content') %>% purrr::pluck(1) %>% purrr::pluck('text')

# Print the model's reply
cat("\n📝 Model Response:\n")
cat(output)
cat("\n")

# Closing message
cat("✅ OpenAI query complete.\n")

# Close out of R, and don't save the environment.
q(save = "no")
