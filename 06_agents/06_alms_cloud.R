#' @name 06_alms_cloud.R
#' @title Using Audio Language Models (ALMs) with Cloud APIs
#' @author Prof. Tim Fraser
#' @description
#' Topic: Audio Language Models
#'
#' This script demonstrates an audio-language model workflow with OpenAI:
#' Sends raw audio + text prompt
#' directly to the model, then print a text response.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

library(httr2) # for HTTP requests
library(jsonlite) # for JSON handling + base64 encoding
library(dplyr) # for simple table display
library(tuneR) # for reading audio files

## 0.2 Environment ###################################

# Load .env in project root
# Expected keys:
# - GEMINI_API_KEY
# - OPENAI_API_KEY
if (file.exists(".env")) { readRenviron(".env") } else { warning(".env file not found. Create one with GEMINI_API_KEY and OPENAI_API_KEY.") }

OPENAI_API_KEY = Sys.getenv("OPENAI_API_KEY")
# Model to use (these change over time, so update if needed)
OPENAI_MODEL = "gpt-4o-audio-preview"


# 1. Working with Audio Files #####################################
# Using tuneR, we're going to read and clip the audio to a nice short 2 seconds.
library(tuneR)
AUDIO_PATH = "06_agents/06_piano.wav"
readWave(AUDIO_PATH) # read in the audio and return a wave object

# Play (in windows, this triggers windows media player)
AUDIO_PATH |> readWave() |> play()

# Extract the first 2 seconds of the audio (the whole clip is 6 seconds long, but much is silent.)
AUDIO_PATH |> readWave()  |> extractWave(from = 0, to = 2, xunit = "time")

# Extract and write to file the first 2 seconds of the audio
AUDIO_PATH |> 
   readWave()  |> 
   extractWave(from = 0, to = 2, xunit = "time") |>
   writeWave("06_agents/06_piano_short.wav")


# 2. AI API Queries for Audio #####################################

# First, we need to make a short helper function to read in the audio and convert it to base64.
# This allows us to send the audio to the API in a format that it can understand.
prepare_audio = function(audio_path) {
  if (!file.exists(audio_path)) { stop(paste0("Audio file not found: ", audio_path)) }
  raw_bytes = readBin(audio_path, "raw", file.info(audio_path)$size)
  audio_base64 = jsonlite::base64_enc(raw_bytes)
  audio_format = tolower(tools::file_ext(audio_path))
  if (audio_format == "") { stop("Could not infer audio format from file extension.") }
  return(list(audio_base64 = audio_base64, audio_format = audio_format))
}

# Let's guestimate how much it would cost to query the audio
# For 20 seconds of audio, it would cost somewhere between 0.0001 and 0.02 USD.

# Use a small audio file while learning, to keep costs tiny.
# Supported formats in these APIs commonly include wav/mp3/aiff/aac/ogg/flac.

# Next, we need to write a function to query the OpenAI API for audio.
query_audio_openai = function(audio_path, prompt, model = OPENAI_MODEL, api_key = OPENAI_API_KEY) {

  # Testing values
  # audio_path = "06_agents/06_piano_short.wav"
  # prompt = "Categorize the audio by type of instrument being played. Return the instrument name in a single sentence. "
  # model = "gpt-4o-audio-preview"
  # api_key = OPENAI_API_KEY

  if (api_key == "") { stop("OPENAI_API_KEY not found. Add it to .env.") }

  # Bundle the audio
  audio = prepare_audio(audio_path)
  url = "https://api.openai.com/v1/chat/completions"

  # Build the request body
  body = list(
    model = model,
    messages = list(
      list(
        role = "user",
        content = list(
          list(type = "text", text = prompt),
          list(
            type = "input_audio",
            input_audio = list(data = audio$audio_base64, format = audio$audio_format)
          )
        )
      )
    )
  )

  # Build the API request
  res = request(url) |>
    req_headers(
      "Content-Type" = "application/json",
      "Authorization" = paste0("Bearer ", api_key)
    ) |>
    req_body_json(body, auto_unbox = TRUE) |>
    req_method("POST")

  # Perform the request
  resp = res |>
    req_perform()

  # Extract json response and return the content
  response_json = resp_body_json(resp)
  # Extract exact content output from the response
  output = response_json$choices[[1]]$message$content
  return(output)
}

# 4. Example 1: Piano Chord #################################

# For our sample audio, we'll use short clips.
# G# Piano Chord
# Source: https://freesound.org/people/blakengouda/sounds/528015/
# Path: 06_agents/06_piano_short.wav
AUDIO_PATH = "06_agents/06_piano_short.wav"

# Prompt to ask both models
PROMPT = paste0(
   "Categorize the audio by type of instrument being played. ",
   "Return the instrument name in a single word. ",
   "For example: \"piano\", \"violin\", \"guitar\", \"drums\", etc."
)

# Safety check before making paid API calls.
if (!file.exists(AUDIO_PATH)) {stop(paste0("Please add an audio file at: ", AUDIO_PATH, "\nTip: keep it short (10-30 sec) to reduce cost while learning."))}
cat("\nSending OpenAI audio query...\n")
time = system.time({
  openai_output = query_audio_openai(audio_path = AUDIO_PATH, prompt = PROMPT, model = OPENAI_MODEL, api_key = OPENAI_API_KEY)
})
cat("\nTime taken: ", round(time[3], 2), " seconds\n")
cat("\nALM output:\n")
openai_output

# Could take about 10 seconds to process.


# 5. Example 2: Piano Chord (2) #################################

# Let's keep working with the piano chord audio.
AUDIO_PATH = "06_agents/06_piano_short.wav"

# Prompt to ask both models
PROMPT = paste0(
  "Return a JSON object with the following fields: ",
  "instrument: (string) the name of the instrument being played, ",
  "confidence: (integer) your level of confidence for the instrument classification, on an integer scale from 1 (no confidence) to 5 (absolutely certain), ",
  "duration: (numeric) the duration of the audio clip in seconds.",
  "notes: (vector of strings) the notes being played, in the format of 'note_name_octave' (e.g. 'C4', 'G#3', 'A#2').",
  "chord: (string) the chord being played, in the format of 'chord_name' (e.g. 'C', 'G#m', 'A#dim').",
  "chord_type: (string) the type of chord being played, in the format of 'major', 'minor', 'diminished', 'augmented', 'major_seventh', 'minor_seventh', 'dominant_seventh', 'half_diminished_seventh', 'diminished_seventh', 'augmented_seventh', 'major_ninth', 'minor_ninth', 'dominant_ninth', 'half_diminished_ninth', 'diminished_ninth', 'augmented_ninth', 'major_eleventh', 'minor_eleventh', 'dominant_eleventh', 'half_diminished_eleventh', 'diminished_eleventh', 'augmented_eleventh', 'major_thirteenth', 'minor_thirteenth', 'dominant_thirteenth', 'half_diminished_thirteenth', 'diminished_thirteenth', 'augmented_thirteenth', 'major_fifteenth', 'minor_fifteenth', 'dominant_fifteenth', 'half_diminished_fifteenth', 'diminished_fifteenth', 'augmented_fifteenth'.",
  "Return no extra tags eg. '```json' or '```'; just return the JSON string. ",
  "Example: '{\"instrument\": \"piano\", \"confidence\": 5, \"duration\": 2.0, \"notes\": [\"C4\", \"G#3\", \"A#2\"], \"chord\": \"C\", \"chord_type\": \"major\"}'",
  "Example: '{\"instrument\": \"saxophone\", \"confidence\": 3, \"duration\": 1.2, \"notes\": [\"F4\", \"G#3\", \"A#2\"], \"chord\": \"Cm\", \"chord_type\": \"minor\"}'"  
)


# Safety check before making paid API calls.
if (!file.exists(AUDIO_PATH)) {stop(paste0("Please add an audio file at: ", AUDIO_PATH, "\nTip: keep it short (10-30 sec) to reduce cost while learning."))}
cat("\nSending OpenAI audio query...\n")
time = system.time({
  openai_output = query_audio_openai(audio_path = AUDIO_PATH, prompt = PROMPT, model = OPENAI_MODEL, api_key = OPENAI_API_KEY)
})
cat("\nTime taken: ", round(time[3], 2), " seconds\n")
cat("\nALM output:\n")
openai_output


# Convert from json to R list
fromJSON(openai_output)
# Here was my output:
# > fromJSON(openai_output)
# $instrument
# [1] "piano"

# $confidence
# [1] 5

# $duration
# [1] 3

# $notes
# [1] "C4" "E4" "G4"

# $chord
# [1] "C"

# $chord_type
# [1] "major"

# In a funny turn of events,
# the model has some things it's good at and some not so great.
# Great at instrument classification
# Not so great at chord recognition - It was actually G# major
# Correctly identified it was a major chord
# Correctly-ish identified the duration (2 seconds)
# Fairly **consistent** - I've run it several times and it's always been the same.


# 5. Example 2: Dog Barks then Whines #################################

# Source: https://freesound.org/people/Jace/sounds/155311/
# Path: 06_agents/06_dog.wav
AUDIO_PATH = "06_agents/06_dog.wav"

PROMPT = paste0(
  "Categorize the audio by type of animal being barked. ",
  "Return the animal name in a single word. ",
  "For example: \"dog\", \"cat\", \"bird\", \"horse\", etc."
)
time = system.time({
  openai_output = query_audio_openai(audio_path = AUDIO_PATH, prompt = PROMPT, model = OPENAI_MODEL, api_key = OPENAI_API_KEY)
})
cat("\nTime taken: ", round(time[3], 2), " seconds\n")
cat("\nALM output:\n")
openai_output

# 6. Example 3: John F Kennedy Speech Clip ####################

# Source: https://freesound.org/people/ERH/sounds/33566/
# Path: 06_agents/06_jfk.wav
AUDIO_PATH = "06_agents/06_jfk.wav"
# Update the AUDIO_PATH to the short version
AUDIO_PATH_SHORT = "06_agents/06_jfk_short.wav"

# Extract and write to file the first 2 seconds of the audio
AUDIO_PATH |> 
   readWave()  |> 
   extractWave(from = 0, to = 2, xunit = "time") |>
   writeWave(AUDIO_PATH_SHORT)


# Prompt to ask both models
PROMPT = paste0(
  "Transcribe the words in the audio into text. ",
  "Return the text in a single string. ",
  "For example: \"Reindeer are better than people.\""
)
time = system.time({
  openai_output = query_audio_openai(audio_path = AUDIO_PATH, prompt = PROMPT, model = OPENAI_MODEL, api_key = OPENAI_API_KEY)
})
cat("\nTime taken: ", round(time[3], 2), " seconds\n")
cat("\nALM output:\n")
openai_output

# I got:
# [1] "\"The fires of frustration and discord are burning in every city.\""

rm(list = ls())
