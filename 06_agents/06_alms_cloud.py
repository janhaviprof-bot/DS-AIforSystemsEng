# 06_alms_cloud.py
# Using Audio Language Models (ALMs) with Cloud APIs
# Pairs with 06_alms_cloud.R
# Tim Fraser
#
# Topic: Audio Language Models
#
# This script demonstrates "true" audio-language model workflows where we send
# raw audio + a text prompt directly to a model API, then get back text output.
# In this Python version, we use OpenAI's chat-completions endpoint for audio.
#
# TuneR equivalent in Python:
# - TuneR::readWave / extractWave / writeWave  ->  librosa + soundfile

# If you haven't already, install these packages...
# pip install requests python-dotenv librosa soundfile

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import base64  # for base64 encoding raw audio bytes
import json  # for parsing JSON-style model output
import os  # for environment variables + file checks
import time  # for timing API requests
from pathlib import Path  # for file extension handling

import librosa  # for reading and clipping audio (TuneR equivalent)
import requests  # for HTTP requests
import soundfile as sf  # for writing .wav files
from dotenv import load_dotenv  # for loading .env file

## 0.2 Environment ###################################

# Load .env in project root.
# Expected keys:
# - OPENAI_API_KEY
if os.path.exists(".env"):
    load_dotenv()
else:
    print(".env file not found. Create one with OPENAI_API_KEY.")

openai_api_key = os.getenv("OPENAI_API_KEY", "")
# Model names change over time, so update this if needed.
openai_model = "gpt-4o-audio-preview"

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found. Add it to .env.")


# 1. WORKING WITH AUDIO FILES #####################################

# Using librosa + soundfile, we'll read and clip audio to a short 2-second chunk.
audio_path = "06_agents/06_piano.wav"
audio_path_short = "06_agents/06_piano_short.wav"

if os.path.exists(audio_path):
    # Read in the audio as a waveform array + sample rate.
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    full_duration = len(y) / sr
    print(f"Loaded audio: {audio_path}")
    print(f"Sample rate: {sr} Hz | Duration: {full_duration:.2f} sec")

    # Extract the first 2 seconds of audio (the original clip has silence).
    clip_seconds = 2
    y_short = y[: int(sr * clip_seconds)]

    # Write the clipped audio to disk.
    sf.write(audio_path_short, y_short, sr)
    print(f"Wrote clipped audio: {audio_path_short}")
else:
    print(f"Audio file not found (skipping clip demo): {audio_path}")


# 2. AI API QUERIES FOR AUDIO #####################################

# First, we need a helper to read audio bytes and convert to base64.
# This is how we package audio for JSON API requests.
def prepare_audio(audio_file_path):
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

    with open(audio_file_path, "rb") as audio_file:
        raw_bytes = audio_file.read()

    audio_base64 = base64.b64encode(raw_bytes).decode("utf-8")
    audio_format = Path(audio_file_path).suffix.lower().lstrip(".")
    if not audio_format:
        raise ValueError("Could not infer audio format from file extension.")

    return {"audio_base64": audio_base64, "audio_format": audio_format}


# Quick cost intuition:
# Small clips are cheap to test with.
# While learning, prefer short audio files (10-30 sec).
# Supported formats commonly include wav/mp3/aiff/aac/ogg/flac.


def query_audio_openai(audio_file_path, prompt, model=openai_model, api_key=openai_api_key):
    """Send audio + text prompt to OpenAI and return text output."""
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found. Add it to .env.")

    audio = prepare_audio(audio_file_path)
    url = "https://api.openai.com/v1/chat/completions"

    # Build the request body.
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio["audio_base64"],
                            "format": audio["audio_format"],
                        },
                    },
                ],
            }
        ],
    }

    # Build + send the POST request.
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    response = requests.post(url, headers=headers, json=body, timeout=180)
    response.raise_for_status()

    # Extract exact content output from response.
    response_json = response.json()
    return response_json["choices"][0]["message"]["content"]


# 4. EXAMPLE 1: PIANO CHORD #################################

# For sample audio, we'll use short clips.
# G# Piano Chord
# Source: https://freesound.org/people/blakengouda/sounds/528015/
# Path: 06_agents/06_piano_short.wav
audio_path = "06_agents/06_piano_short.wav"

prompt = (
    "Categorize the audio by type of instrument being played. "
    "Return the instrument name in a single word. "
    'For example: "piano", "violin", "guitar", "drums", etc.'
)

# Safety check before making paid API calls.
if not os.path.exists(audio_path):
    raise FileNotFoundError(
        f"Please add an audio file at: {audio_path}\n"
        "Tip: keep it short (10-30 sec) to reduce cost while learning."
    )

print("\nSending OpenAI audio query...")
start_time = time.time()
openai_output = query_audio_openai(audio_file_path=audio_path, prompt=prompt)
elapsed = time.time() - start_time
print(f"\nTime taken: {elapsed:.2f} seconds")
print("\nALM output:")
print(openai_output)

# Could take about ~10 seconds to process.


# 5. EXAMPLE 2: PIANO CHORD (JSON OUTPUT) #################################

# Let's keep working with the same piano chord clip.
audio_path = "06_agents/06_piano_short.wav"

prompt = (
    "Return a JSON object with the following fields: "
    "instrument: (string) the name of the instrument being played, "
    "confidence: (integer) your confidence from 1 (low) to 5 (high), "
    "duration: (numeric) the duration of the audio clip in seconds, "
    "notes: (vector of strings) notes played, in the format note_name_octave (e.g. C4, G#3), "
    "chord: (string) the chord name (e.g. C, G#m, A#dim), "
    "chord_type: (string) chord type such as major, minor, diminished, augmented. "
    "Return no extra tags like ```json or ```. Return only the JSON string."
)

if not os.path.exists(audio_path):
    raise FileNotFoundError(
        f"Please add an audio file at: {audio_path}\n"
        "Tip: keep it short (10-30 sec) to reduce cost while learning."
    )

print("\nSending OpenAI audio query...")
start_time = time.time()
openai_output = query_audio_openai(audio_file_path=audio_path, prompt=prompt)
elapsed = time.time() - start_time
print(f"\nTime taken: {elapsed:.2f} seconds")
print("\nALM output:")
print(openai_output)

# Convert from JSON string to Python dictionary.
try:
    parsed = json.loads(openai_output)
    print("\nParsed JSON:")
    print(parsed)
except json.JSONDecodeError:
    print("\nCould not parse model output as JSON. Rerun or tighten prompt constraints.")

# In a funny turn of events, these models usually have some things they do
# very well (instrument classification), and some things less well
# (exact chord recognition can be inconsistent).

# My Parsed JSON:
# {'instrument': 'piano', 'confidence': 4, 'duration': 12.5, 'notes': ['C4', 'E4', 'G4'], 'chord': 'C', 'chord_type': 'major'}


# 6. EXAMPLE 3: DOG BARKS THEN WHINES #################################

# Source: https://freesound.org/people/Jace/sounds/155311/
# Path: 06_agents/06_dog.wav
audio_path = "06_agents/06_dog.wav"

prompt = (
    "Categorize the audio by type of animal being barked. "
    "Return the animal name in a single word. "
    'For example: "dog", "cat", "bird", "horse", etc.'
)

if os.path.exists(audio_path):
    start_time = time.time()
    openai_output = query_audio_openai(audio_file_path=audio_path, prompt=prompt)
    elapsed = time.time() - start_time
    print(f"\nTime taken: {elapsed:.2f} seconds")
    print("\nALM output:")
    print(openai_output)
else:
    print(f"\nSkipping dog example; file not found: {audio_path}")


# 7. EXAMPLE 4: JOHN F KENNEDY SPEECH CLIP ####################

# Source: https://freesound.org/people/ERH/sounds/33566/
# Path: 06_agents/06_jfk.wav
audio_path = "06_agents/06_jfk.wav"
audio_path_short = "06_agents/06_jfk_short.wav"

# Extract + write first 2 seconds if source file exists.
if os.path.exists(audio_path):
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    y_short = y[: int(sr * 2)]
    sf.write(audio_path_short, y_short, sr)
    print(f"\nWrote clipped JFK audio: {audio_path_short}")

    prompt = (
        "Transcribe the words in the audio into text. "
        "Return the text in a single string. "
        'For example: "Reindeer are better than people."'
    )

    start_time = time.time()
    openai_output = query_audio_openai(audio_file_path=audio_path_short, prompt=prompt)
    elapsed = time.time() - start_time
    print(f"\nTime taken: {elapsed:.2f} seconds")
    print("\nALM output:")
    print(openai_output)
else:
    print(f"\nSkipping JFK example; file not found: {audio_path}")
