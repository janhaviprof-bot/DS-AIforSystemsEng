#' @name 05_vlms_cloud.R
#' @title Using Visual Language Models (VLMs) with Ollama Cloud
#' @author Prof. Tim Fraser
#' @description
#' Topic: Visual Language Models
#'
#' What if our AI systems could see, not just read?
#' This script shows how to send an image to a vision-capable model
#' (like gemma3:4b) using ollama cloud!

# Read about your a models info in the ollama library:
# eg. for gemma3, we'll find its multimodal (vision) version, gemma3:4b
# https://ollama.com/library/gemma3


# 0. SETUP ###################################

## Example Image
# Today, we'll be using an example image from Unsplash.
# (Great place to get free pictures for your projects!)
# Photo by Toa Heftiba 
# Source Link: https://unsplash.com/photos/people-eating-inside-of-cafeteria-during-daytime-6bKpHAun4d8
# Creator Link: https://unsplash.com/@heftiba?utm_source=unsplash&utm_medium=referral&utm_content=creditCopyText">Toa Heftiba</a> on <a href="https://unsplash.com/photos/people-eating-inside-of-cafeteria-during-daytime-6bKpHAun4d8?utm_source=unsplash&utm_medium=referral&utm_content=creditCopyText

# It shows a bunch of people in a coffee shop.

# Let's say, we want to count the number of people in the image.
# There are creepy uses of this, sure, but also some legitimate uses.
# Evacuation - can we take a quick picture of a shelter to count the number of people?
# Crowd detection - can we see how many people are in a room?
# Object detection - can we see if there are any objects in the image?
# Face detection - can we see if there are any faces in the image?
# Text detection - can we see if there are any text in the image?
# License plate detection - can we see if there are any license plates in the image?
# Car detection - can we see if there are any cars in the image?
# Pedestrian detection - can we see if there are any pedestrians in the image?

# An ethical system would perform the count, and then *delete the image*.
# That way, we don't have to worry about the image being used for something nefarious.
# But, for now, we'll just use the image as is.



## 0.1 Load Packages #################################

library(dplyr) # for data wrangling
library(magick) # for image processing
library(httr2) # for HTTP requests
library(jsonlite) # for JSON handling

# 0.2 Image Processing #################################

# First step: We need to downscale the image.
# This is because the model has a context length limit.
# We can't send the full image to the model.
# We need to downscale the image to a size that the model can handle.
# We can use the magick package's image_read(), image_info(), and image_scale() functions to do this.


# Path to the image we want the VLM to analyze
IMAGE_PATH = "06_agents/05_coffeeshop.jpg"

img = IMAGE_PATH |> image_read()
info = img |> image_info() # check image size
info # view image info

# Shrink the image to 50% of its original size
new_size = paste0(info$width * 0.5, "x", info$height * 0.5)
# Scale the image to the new size
img_small = img |> image_scale(new_size)
# Recheck the image size
img_small |> image_info() 

# Make a new path for the small image
IMAGE_PATH_SMALL = "06_agents/05_coffeeshop_small.jpg"
# Write the small image to a file
img_small |> image_write(path = IMAGE_PATH_SMALL)


## 0.2 Environment ###################################

# Load .env (contains OLLAMA_API_KEY for the cloud fallback)
if (file.exists(".env")){  readRenviron(".env")  } else {  warning(".env file not found. Needed only for the cloud fallback in Section 2.") }


## 0.3 Configuration #################################

# Gemma3:4b is a multimodal model that can read images AND text
MODEL = "gemma3:4b"

# Path to the image we want the VLM to analyze
IMAGE_PATH = "06_agents/05_coffeeshop_small.jpg"

# The prompt we pair with the image
PROMPT = "Analyze this image and count the number of people in the image."

# Make sure the image actually exists before we send it
if (!file.exists(IMAGE_PATH)) { stop(paste0("Image not found: ", IMAGE_PATH)) }


# 2. CLOUD VLM WITH HTTR2 (ALTERNATIVE) ###########

# If you don't have Ollama running locally, uncomment this
# section and comment out Section 1 above.
# You will need an OLLAMA_API_KEY in your .env file.

library(httr2)    # for HTTP requests
library(jsonlite) # for JSON handling

MODEL = "gemma3:4b"
# Retrieve API key from environment
if (file.exists(".env")){  readRenviron(".env")  } else {  warning(".env file not found. Make sure it exists in the project root.") }
OLLAMA_API_KEY = Sys.getenv("OLLAMA_API_KEY")
if (OLLAMA_API_KEY == "") { stop("OLLAMA_API_KEY not found in .env file.") }

# Let's write ourselves a short function to perform the query
query = function(IMAGE_PATH, PROMPT, MODEL, OLLAMA_API_KEY){

  # Read the image and base64-encode it for the API
  raw_bytes = readBin(IMAGE_PATH, "raw", file.info(IMAGE_PATH)$size)
  image_base64 = jsonlite::base64_enc(raw_bytes)

  # Build the request body (matches the Ollama chat API format)
  body = list(
    model = MODEL,
    messages = list(
      list(
        role = "user",
        content = PROMPT,
        images = list(image_base64)
      )
    ),
    stream = FALSE
  )

  # POST to Ollama Cloud with bearer-token auth
  res = request("https://ollama.com/api/chat") %>%
    req_headers(
      "Authorization" = paste0("Bearer ", OLLAMA_API_KEY),
      "Content-Type" = "application/json"
    ) %>%
    req_body_json(body) %>%
    req_method("POST") %>%
    req_perform()

  # Parse the JSON response and extract the model's reply
  response = resp_body_json(res)
  output = response$message$content

  return(output)
}


output = query(IMAGE_PATH, PROMPT, MODEL, OLLAMA_API_KEY)

cat("\nVLM Response (cloud):\n")
cat(output)
cat("\n")

# 3. Machine Readable Output #################################

# Often, if you're doing this kind of work, we want to get a machine readable output.
# I suggest asking the llm to output a JSON string with the answer.

PROMPT2 = paste0(
  "Analyze this image and count the number of people in the image. ",
  "Output the answer in a JSON string. ",
  "Do not include any other text in your response. ",
  "Do not include any extra formatting like  '```json' in your response. ",
  "The JSON string should have the following format: ",
  "{",
  "  \"n_sitting\": \"<total number of people sitting here>\",",
  "  \"n_standing\": \"<total number of people standing here>\"",
  "}"
)
# Preview the prompt
cat(PROMPT2)

# Send the prompt to the model
resp2 = query(IMAGE_PATH, PROMPT2, MODEL, OLLAMA_API_KEY)
# Preview the response
cat(resp2)

# Parse the JSON string into an R list, using fromJSON() from the jsonlite package
json = fromJSON(resp2)
# Preview the JSON list
print(json)


# Print the number of people sitting and standing
cat(paste0("Number of people sitting: ", json$n_sitting, "\n"))
cat(paste0("Number of people standing: ", json$n_standing, "\n"))

# 3. CLEAN UP ######################################
rm(list = ls())
