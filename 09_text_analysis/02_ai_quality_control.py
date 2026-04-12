# 02_ai_quality_control.py
# AI-Assisted Text Quality Control
# Tim Fraser

# This script demonstrates how to use AI (Ollama or OpenAI) to perform quality control
# on AI-generated text reports. It implements quality control criteria including
# boolean accuracy checks and Likert scales for multiple quality dimensions.
# Students learn to design quality control prompts and structure AI outputs as JSON.

# 0. Setup #################################

## 0.1 Load Packages #################################

# If you haven't already, install required packages:
# pip install pandas requests python-dotenv

import pandas as pd  # for data wrangling
import re  # for text processing
import requests  # for HTTP requests
import json  # for JSON operations
import os  # for environment variables
from dotenv import load_dotenv  # for loading .env file

## 0.2 Configuration #################################

# Choose your AI provider: "ollama" or "openai"
AI_PROVIDER = "openai"  # Change to "openai" if using OpenAI

# Ollama configuration
PORT = 11434
OLLAMA_HOST = f"http://localhost:{PORT}"
OLLAMA_MODEL = "llama3.2:latest"  # Use a model that supports JSON output

# OpenAI configuration
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"  # Low-cost model

## 0.3 Load Sample Data #################################

# Load sample report text for quality control
with open("09_text_analysis/data/sample_reports.txt", "r", encoding="utf-8") as f:
    sample_text = f.read()

# Split text into individual reports
reports = [r.strip() for r in sample_text.split("\n\n") if r.strip()]
report = reports[0]

# Load source data (if available) for accuracy checking
# In this example, we'll use a simple data structure
source_data = """White County, IL | 2015 | PM10 | Time Driven | hours
|type        |label_value |label_percent |
|:-----------|:-----------|:-------------|
|Light Truck |2.7 M       |51.8%         |
|Car/ Bike   |1.9 M       |36.1%         |
|Combo Truck |381.3 k     |7.3%          |
|Heavy Truck |220.7 k     |4.2%          |
|Bus         |30.6 k      |0.6%          |"""

print("📝 Report for Quality Control:")
print("---")
print(report)
print("---\n")

# 1. AI Quality Control Function #################################

## 1.1 Create Quality Control Prompt #################################

# Create a comprehensive quality control prompt based on samplevalidation.tex
# This prompt asks the AI to evaluate text on multiple criteria
def create_quality_control_prompt(report_text, source_data=None):
    # Base instructions for quality control
    instructions = "You are a quality control validator for AI-generated reports. Evaluate the following report text on multiple criteria and return your assessment as valid JSON."
    
    # Add source data if provided for accuracy checking
    data_context = ""
    if source_data is not None:
        data_context = f"\n\nSource Data:\n{source_data}\n"
    
    # Quality control criteria (from samplevalidation.tex)
    criteria = """
  
Quality Control Criteria:

1. **accurate** (boolean): Are there any factual errors or unsupported interpretations relative to the Source Data section?.Verify that no part of the paragraph misinterprets the data supplied. Return TRUE if no misinterpretation. FALSE if any problems.

2. **accuracy** (1-5 Likert scale): How severe are the problems interpreting the Data? Rank the paragraph on a 5-point Likert scale, where 1 = many problems interpreting the Data vs. 5 = no misinterpretation of the Data. If accurate == TRUE, accuracy should be greater than equal to 3. If accurate == FALSE, accuracy should be less than equal to 3.

3. **formality** (1-5 Likert scale): How formal is the tone of the paragraph? Rank the paragraph on a 5-point Likert scale, where 1 = casual writing vs. 5 = government report writing.

4. **faithfulness** (1-5 Likert scale): Are claims related to what the data says? Rank the paragraph on a 5-point Likert scale, where 1 = makes grandiose claims not supported by the data vs. 5 = makes claims directly related to the data.

5. **clarity** (1-5 Likert scale): Is the writing easy to understand? Rank the paragraph on a 5-point Likert scale, where 1 = confusing writing style vs. 5 = clear and precise.

6. **succinctness** (1-5 Likert scale): Is the text too wordy? Rank the paragraph on a 5-point Likert scale, where 1 = unnecessarily wordy vs. 5 = succinct.

7. **relevance** (1-5 Likert scale): Is the content on topic for the task without any irrelevant commentary? Rank the paragraph on a 5-point Likert scale, where 1 = irrelevant commentary vs. 5 = relevant commentary about the data.

Return your response as valid JSON in this exact format:
{
  "accurate": true/false,
  "accuracy": 1-5,
  "formality": 1-5,
  "faithfulness": 1-5,
  "clarity": 1-5,
  "succinctness": 1-5,
  "relevance": 1-5,
  "details": "0-50 word explanation of your assessment"
}
"""
    
    # Combine into full prompt
    full_prompt = f"{instructions}{data_context}\n\nReport Text to Validate:\n{report_text}{criteria}"
    
    return full_prompt

## 1.2 Query AI Function #################################

# Function to query AI and get quality control results
def query_ai_quality_control(prompt, provider=AI_PROVIDER):
    if provider == "ollama":
        # Query Ollama
        url = f"{OLLAMA_HOST}/api/chat"
        
        body = {
            "model": OLLAMA_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "format": "json",  # Request JSON output
            "stream": False
        }
        
        response = requests.post(url, json=body)
        response.raise_for_status()
        response_data = response.json()
        output = response_data["message"]["content"]
        
    elif provider == "openai":
        # Query OpenAI
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in .env file. Please set it up first.")
        
        url = "https://api.openai.com/v1/chat/completions"
        
        body = {
            "model": OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a quality control validator. Always return your responses as valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "response_format": {"type": "json_object"},  # Request JSON output
            "temperature": 0.3  # Lower temperature for more consistent validation
        }
        
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        response_data = response.json()
        output = response_data["choices"][0]["message"]["content"]
        
    else:
        raise ValueError("Invalid provider. Use 'ollama' or 'openai'.")
    
    return output

## 1.3 Parse Quality Control Results #################################

# Parse JSON response and convert to DataFrame
def parse_quality_control_results(json_response):
    # Try to parse JSON
    # Sometimes AI returns text with JSON, so we extract JSON if needed
    json_match = re.search(r"\{.*\}", json_response, re.DOTALL)
    if json_match:
        json_response = json_match.group(0)
    
    # Parse JSON
    quality_data = json.loads(json_response)
    
    # Convert to DataFrame
    results = pd.DataFrame({
        "accurate": [quality_data["accurate"]],
        "accuracy": [quality_data["accuracy"]],
        "formality": [quality_data["formality"]],
        "faithfulness": [quality_data["faithfulness"]],
        "clarity": [quality_data["clarity"]],
        "succinctness": [quality_data["succinctness"]],
        "relevance": [quality_data["relevance"]],
        "details": [quality_data["details"]]
    })
    
    return results

# 2. Run Quality Control #################################

## 2.1 Create Quality Control Prompt #################################

quality_prompt = create_quality_control_prompt(report, source_data)

print("🤖 Querying AI for quality control...\n")

## 2.2 Query AI #################################

ai_response = query_ai_quality_control(quality_prompt, provider=AI_PROVIDER)

print("📥 AI Response (raw):")
print(ai_response)
print()

## 2.3 Parse and Display Results #################################

quality_results = parse_quality_control_results(ai_response)

print("✅ Quality Control Results:")
print(quality_results)
print()

## 2.4 Calculate Overall Score #################################

# Calculate average Likert score (excluding boolean accurate)
likert_scores = quality_results[["accuracy", "formality", "faithfulness", "clarity", "succinctness", "relevance"]]
overall_score = likert_scores.mean(axis=1).values[0]

quality_results["overall_score"] = round(overall_score, 2)

print(f"📊 Overall Quality Score (average of Likert scales): {overall_score:.2f} / 5.0")
print(f"📊 Accuracy Check: {'✅ PASS' if quality_results['accurate'].values[0] else '❌ FAIL'}\n")

# 3. Quality Control Multiple Reports #################################

## 3.1 Batch Quality Control Function #################################

# Function to check multiple reports
def check_multiple_reports(reports, source_data=None):
    print(f"🔄 Performing quality control on {len(reports)} reports...\n")
    
    all_results = []
    
    for i, report_text in enumerate(reports, 1):
        print(f"Checking report {i} of {len(reports)}...")
        
        # Create prompt
        prompt = create_quality_control_prompt(report_text, source_data)
        
        # Query AI
        try:
            response = query_ai_quality_control(prompt, provider=AI_PROVIDER)
            results = parse_quality_control_results(response)
            results["report_id"] = i
            all_results.append(results)
        except Exception as e:
            print(f"❌ Error checking report {i}: {e}")
        
        # Small delay to avoid rate limiting
        import time
        time.sleep(1)
    
    # Combine all results
    if all_results:
        combined_results = pd.concat(all_results, ignore_index=True)
        return combined_results
    else:
        return pd.DataFrame()

## 3.2 Run Batch Quality Control (Optional) #################################

# Uncomment to check all reports
# if len(reports) > 1:
#     batch_results = check_multiple_reports(reports, source_data)
#     print("\n📊 Batch Quality Control Results:")
#     print(batch_results)

print("✅ AI quality control complete!")
print("💡 Compare these results with manual quality control (01_manual_quality_control.py) to see how AI performs.")
