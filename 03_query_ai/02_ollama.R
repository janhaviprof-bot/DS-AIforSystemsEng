# workflow.R

# A script to query the lightweight LLM gemma-3-1b!

# Starting message
cat("\n🚀 Sending LLM query in R...\n")

# If you haven't already, install these packages...
# install.packages(c("httr2", "jsonlite"))

# Load libraries
library(httr2)    # For HTTP requests
library(jsonlite) # For working with JSON

PORT = 11434
OLLAMA_HOST = paste0("http://localhost:", PORT)
url = paste0("http://localhost:", PORT, "/api/generate")

# Construct the request body as a list
body <- list(
  model = "smollm2:1.7b", # Model name
  prompt = "Is model working?",        # User prompt
  stream = FALSE       # Non-streaming response
)

# Build and send the POST request to the LM Studio REST API
res <- request(url) %>%
  req_body_json(body) %>%   # Attach the JSON body
  req_method("POST") %>%   # Set HTTP method
  req_perform()             # Execute the request

# Parse the response JSON
response <- resp_body_json(res)

# Extract the model's reply as a character string
output = response$choices[[1]]$message$content

# Print the model's reply
cat(output)

# Closing message
cat("\n✅ LLM query complete. Exiting R...\n")

# Close out of R, and don't save the environment.
q(save = "no")