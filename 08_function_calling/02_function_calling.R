# 03_function_calling.R

# This script demonstrates how to use the ollamar package in R to interact with an LLM that supports function calling.

# Further reading: https://cran.r-project.org/web/packages/ollamar/vignettes/ollamar.html

# Load packages
require(ollamar)
require(dplyr)
require(stringr)

# Select model of interest
MODEL = "smollm2:1.7b"

# Define a function to be used as a tool
add_two_numbers = function(x, y){
    return(x + y)
}

# Define the tool metadata as a list
tool_add_two_numbers = list(
    type = "function",
    "function" = list(
        name = "add_two_numbers",
        description = "Add two numbers",
        parameters = list(
            type = "object",
            required = list("x", "y"),
            properties = list(
                x = list(type = "numeric", description = "first number"),
                y = list(type = "numeric", description = "second number")
            )
        )
    )
)

# Create a simple chat history with a user question that will require the tool
messages = create_message(role = "user", content = "What is 3 + 2?")
resp = chat(model = MODEL, messages = messages, tools = list(tool_add_two_numbers), output = "tools", stream = FALSE)

# Receive back the tool call
tool = resp[[1]]
# Execute the tool call
do.call(tool$name, tool$arguments)

# Clean up shop
rm(list = ls())
