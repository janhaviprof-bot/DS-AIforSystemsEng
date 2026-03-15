#' @name 05_vlms_local.R
#' @title Using Visual Language Models (VLMs) with Ollama (local)
#' @author Prof. Tim Fraser
#' @description
#' Topic: Visual Language Models
#'
#' What if our AI systems could see, not just read?
#' This script shows how to send an image to a vision-capable model
#' (like llava) using ollamar (local).

# Read about your a models info in the ollama library:
# https://ollama.com/library/llava

# **NOTE** ------------------------------------
# Running vision queries can take a LONG time on a local machine.
# You might want to use the cloud version instead.
# **See 05_vlms_cloud.R!**


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

# ollamar talks directly to a locally running Ollama server
library(ollamar) # for local ollama queries
library(dplyr) # for data wrangling
library(magick) # for image processing

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

# Shrink the image to 10% of its original size
new_size = paste0(info$width * 0.5, "x", info$height * 0.5)
# Scale the image to the new size
img_small = img |> image_scale(new_size)
# Recheck the image size
img_small |> image_info() 

# Make a new path for the small image
IMAGE_PATH_SMALL = "06_agents/05_coffeeshop_small.jpg"
# Write the small image to a file
img_small |> image_write(path = IMAGE_PATH_SMALL)


## 0.3 Environment ###################################

# Load .env (contains OLLAMA_API_KEY for the cloud fallback)
if (file.exists(".env")){  readRenviron(".env")  } else {  warning(".env file not found. Needed only for the cloud fallback in Section 2.") }


## 1. Configuration #################################

# LLaVA is a multimodal model that can read images AND text
# Remember, you'll need to pull the model first with `ollama pull llava` in bash
MODEL = "llava"

# Path to the image we want the VLM to analyze
IMAGE_PATH_SMALL = "06_agents/05_coffeeshop_small.jpg"

# The prompt we pair with the image
PROMPT = "Analyze this image and count the number of people in the image."

# Make sure the image actually exists before we send it
if (!file.exists(IMAGE_PATH)) { stop(paste0("Image not found: ", IMAGE_PATH)) }


# 2. Launch Ollama from inside R (asynchronous)

# Configuration
PORT = 11434
OLLAMA_HOST = paste0("127.0.0.1:", PORT)
OLLAMA_LOG = tempfile("ollama_serve_", fileext = ".log")

# Set environment variables for this R session
Sys.setenv(OLLAMA_HOST = OLLAMA_HOST)
Sys.setenv(OLLAMA_CONTEXT_LENGTH = "32000")

# Start `ollama serve` in the background so R stays usable
system2("ollama", args = "serve", wait = FALSE, stdout = OLLAMA_LOG, stderr = OLLAMA_LOG)


# Wait briefly for server readiness before the first chat call
Sys.sleep(0.5)


# 3. LOCAL VLM WITH OLLAMAR #######################

# Build a message list with an `images` field
# ollamar base64-encodes the file for us automatically
messages = list(
  list(
    role = "user",
    content = PROMPT,
    images = IMAGE_PATH
  )
)

# Send the image + prompt to the local Ollama VLM
resp = chat(model = MODEL, messages = messages, output = "text", stream = FALSE)

# It takes a WHILE! 
# (about ~2 minutes on my machine).

# For me, llava model said:
# In the image, I see a total of nine individuals. 
# The people are engaged in various activities 
# such as sitting at tables, standing, or walking around. 
# There are two individuals standing near the center of the image, 
# one person standing at the far end, and six seated at tables. "

# For me, gemma3:4b model said:

cat("\nVLM Response (ollamar):\n")
resp


# Clean up!
rm(list = ls())