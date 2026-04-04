# 07_parallel_queries.R

# Can we send queries to multiple agents at once? Yes!

# Load packages
library(httr2) # for HTTP requests
library(dplyr) # for data wrangling
library(readr) # for reading text files
library(jsonlite) # for JSON handling
library(purrr) # for list-wise operations
library(stringr) # for string extraction

# 1. CONCEPT ###################################

# Here's an example where we can do basic 'qualitative coding' / 'content analysis'very very quickly.
# Content analysis is the process of systematically examining and categorizing textual data to identify patterns, themes, and insights.
# Sociologists, anthropologists, and market researchers have been doing this for decades.
# It's the primary way to analyze focus group, interviews, reviews, and other qualitative data.
# You as a human being have been doing this your whole life, without even knowing it!

# A friend tells you what they thought of a movie. You categorize in your head as "they liked it" or "they didn't like it".
# If we provide an LLM with really good, standardized instructions,
# it can do this for us very quickly.

# text to classify
texts = read_csv("06_agents/07_feedback.csv") %>%
   sample_n(10) # Let's take a random sample of 10

# Make a quick wrapper function for a request
get_request = function(CONTENT, PROMPT, MODEL){
    
    PORT = 11434
    OLLAMA_HOST = paste0("http://localhost:", PORT)
    url = paste0("http://localhost:", PORT, "/api/chat")

    # We're going to use the /api/chat endpoint,
    # which allows us to send a list of messages, not just a single prompt.

    # Construct the request body as a list
    body = list(
        model = MODEL, # Model name
        messages = list(
            list(role = "system", content = PROMPT),
            list(role = "user", content = CONTENT)  ),
        stream = FALSE       # Non-streaming response
    )

    # Build and send the POST request to the REST API
    req = httr2::request(url) %>%
        req_body_json(body) %>%   # Attach the JSON body
        req_method("POST")   # Set HTTP method

    # Return the request object, BEFORE it is sent.
    return(req)
}


# Create a system prompt, asking it to return a json string
PROMPT = paste0(
    "Your only task/role is to evaluate the sentiment of product reviews provided by the user. ",
    "Your response should simply be 'positive', 'negative', or 'other'. ",
    "Return a JSON string of your response. ",
    "Do not include any other text in your response. ",
    "Do not include any extra formatting like  '```json' in your response. ",
    "The JSON string should have the following format: ",
    "{",
    "  \"sentiment\": \"<sentiment of the review>\",",
    "}"
)

MODEL = "smollm2:1.7b"

# Do one quick test request
resp = get_request(CONTENT = "booo", PROMPT = PROMPT, MODEL = MODEL) |>
    req_perform()
    
# Check the output!
resp |> resp_body_json() |> with(message) |> with(content)


# Create a list of request objects, BEFORE they are sent.
reqs = texts$feedback |>
   map(~get_request(CONTENT = ., PROMPT = PROMPT, MODEL = MODEL)) 

# Send the requests in parallel and time the operation
time = system.time({
    # make parallel requests and get response
    resps = req_perform_parallel(reqs)
})
cat("\n Time taken to send", length(reqs), "requests: ", round(time[3], 2), " seconds\n")

# View the results!
resps |> 
   map(~resp_body_json(.x) |> with(message) |> with(content) ) 

# Usually, there will be a few deviations in formatting,
# so you'll probably want to use string extraction
# to get a nice clean result.

resps |> 
   # For each response, extract the content
   map_chr(~resp_body_json(.x) |> with(message) |> with(content) )  %>%
   # Standardize to lower case, just in case
   tolower() %>%
   # Extract the keywords you asked them to code
   # In REGEX string pattern matching,
   # "|" means OR
   stringr::str_extract("positive|negative|other")

rm(list = ls())