# 02_example_r.R

# This script can be run in R to demonstrate 
# how to make an API request

# Install if you haven’t yet
# install.packages(c(“httr2”, “jsonlite”)) 

# Execute query and save response as object
library(httr2)
library(jsonlite)

# Load environment variables from .env file
readRenviron(".env")
TEST_API_KEY = Sys.getenv("TEST_API_KEY")

# Create request object
req = request("https://reqres.in/api/users/2") |>
  req_headers(`x-api-key` = TEST_API_KEY) |>
  req_method("GET")

# Execute request and store result as object
resp = req_perform(req)

# Check status
resp$status_code # 200 = success
# Return response as a json
resp_body_json(resp)

# Or use this if you want to convert the response to a string first and then to a list
fromJSON(resp_body_string(resp))

# Clear environment
rm(list = ls())

# Exit
# q(save = "no")