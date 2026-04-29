# 02_ai_quality_control.R
# AI-Assisted Text Quality Control
# Tim Fraser

# This script demonstrates how to use AI (Ollama or OpenAI) to perform quality control
# on AI-generated text reports. It implements quality control criteria including
# boolean accuracy checks and Likert scales for multiple quality dimensions.
# Students learn to design quality control prompts and structure AI outputs as JSON.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

# If you haven't already, install required packages:
# install.packages(c("dplyr", "stringr", "readr", "httr2", "jsonlite"))

library(dplyr)    # for data wrangling
library(stringr)  # for text processing
library(readr)    # for reading files
library(httr2)    # for HTTP requests
library(jsonlite) # for JSON operations

## 0.2 Configuration ####################################

# Choose your AI provider: "ollama" or "openai"
AI_PROVIDER = "ollama"  # Change to "openai" if using OpenAI

# Ollama configuration
PORT = 11434
OLLAMA_HOST = paste0("http://localhost:", PORT)
OLLAMA_MODEL = "llama3.2:latest"  # Use a model that supports JSON output

# OpenAI configuration
if (file.exists(".env")){  readRenviron(".env")  } else {  warning(".env file not found. Make sure it exists in the project root.") }
OPENAI_API_KEY = Sys.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"  # Low-cost model

## 0.3 Load Sample Data ####################################

# Load sample report text for quality control
sample_text = read_file("09_text_analysis/data/sample_reports.txt")
reports = strsplit(sample_text, "\n\n")[[1]]
reports = trimws(reports)
reports = reports[reports != ""]  # Remove empty strings
report = reports[1]

# Load source data (if available) for accuracy checking
# In this example, we'll use a simple data structure
source_data = "White County, IL | 2015 | PM10 | Time Driven | hours
|type        |label_value |label_percent |
|:-----------|:-----------|:-------------|
|Light Truck |2.7 M       |51.8%         |
|Car/ Bike   |1.9 M       |36.1%         |
|Combo Truck |381.3 k     |7.3%          |
|Heavy Truck |220.7 k     |4.2%          |
|Bus         |30.6 k      |0.6%          |"

cat("📝 Report for Quality Control:\n")
cat("---\n")
cat(report)
cat("\n---\n\n")

# 1. AI QUALITY CONTROL FUNCTION ###################################

## 1.1 Create Quality Control Prompt #################################

# Create a comprehensive quality control prompt based on samplevalidation.tex
# This prompt asks the AI to evaluate text on multiple criteria
create_quality_control_prompt = function(report_text, source_data = NULL) {
  
  # Base instructions for quality control
  instructions = paste0(
    "You are a quality control validator for AI-generated reports. ",
    "Evaluate the following report text on multiple criteria and return your assessment as valid JSON."
  )
  # Add source data if provided for accuracy checking
  data_context = ""
  if (!is.null(source_data)) {
    data_context = paste0("\n\nSource Data:\n", source_data, "\n")
  }
  
  # Quality control criteria (from samplevalidation.tex)
  criteria = "
  
Quality Control Criteria:

1. **accurate** (boolean): Verify that no part of the paragraph misinterprets the data supplied. Return TRUE if no misinterpretation. FALSE if any problems.

2. **accuracy** (1-5 Likert scale): Rank the paragraph on a 5-point Likert scale, where 1 = many problems interpreting the Data vs. 5 = no misinterpretation of the Data.

3. **formality** (1-5 Likert scale): Rank the paragraph on a 5-point Likert scale, where 1 = casual writing vs. 5 = government report writing.

4. **faithfulness** (1-5 Likert scale): Rank the paragraph on a 5-point Likert scale, where 1 = makes grandiose claims not supported by the data vs. 5 = makes claims directly related to the data.

5. **clarity** (1-5 Likert scale): Rank the paragraph on a 5-point Likert scale, where 1 = confusing writing style vs. 5 = clear and precise.

6. **succinctness** (1-5 Likert scale): Rank the paragraph on a 5-point Likert scale, where 1 = unnecessarily wordy vs. 5 = succinct.

7. **relevance** (1-5 Likert scale): Rank the paragraph on a 5-point Likert scale, where 1 = irrelevant commentary vs. 5 = relevant commentary about the data.

Return your response as valid JSON in this exact format:
{
  \"accurate\": true/false,
  \"accuracy\": 1-5,
  \"formality\": 1-5,
  \"faithfulness\": 1-5,
  \"clarity\": 1-5,
  \"succinctness\": 1-5,
  \"relevance\": 1-5,
  \"details\": \"0-50 word explanation of your assessment\"
}
"
  
  # Combine into full prompt
  full_prompt = paste0(
    instructions,
    data_context,
    "\n\nReport Text to Validate:\n",
    report_text,
    criteria
  )
  
  return(full_prompt)
}

## 1.2 Query AI Function #################################

# Function to query AI and get quality control results
query_ai_quality_control = function(prompt, provider = AI_PROVIDER) {
  
  if (provider == "ollama") {
    # Query Ollama
    url = paste0(OLLAMA_HOST, "/api/chat")
    
    body = list(
      model = OLLAMA_MODEL,
      messages = list(
        list(
          role = "user",
          content = prompt
        )
      ),
      format = "json",  # Request JSON output
      stream = FALSE
    )
    
    res = request(url) %>%
      req_body_json(body) %>%
      req_method("POST") %>%
      req_perform()
    
    response = resp_body_json(res)
    output = response$message$content
    
  } else if (provider == "openai") {
    # Query OpenAI
    if (OPENAI_API_KEY == "") {
      stop("OPENAI_API_KEY not found in .env file. Please set it up first.")
    }
    
    url = "https://api.openai.com/v1/chat/completions"
    
    body = list(
      model = OPENAI_MODEL,
      messages = list(
        list(
          role = "system",
          content = "You are a quality control validator. Always return your responses as valid JSON."
        ),
        list(
          role = "user",
          content = prompt
        )
      ),
      response_format = list(type = "json_object"),  # Request JSON output
      temperature = 0.3  # Lower temperature for more consistent validation
    )
    
    res = request(url) %>%
      req_headers(
        "Authorization" = paste0("Bearer ", OPENAI_API_KEY),
        "Content-Type" = "application/json"
      ) %>%
      req_body_json(body) %>%
      req_method("POST") %>%
      req_perform()
    
    response = resp_body_json(res)
    output = response$choices[[1]]$message$content
    
  } else {
    stop("Invalid provider. Use 'ollama' or 'openai'.")
  }
  
  return(output)
}

## 1.3 Parse Quality Control Results #################################

# Parse JSON response and convert to tibble
parse_quality_control_results = function(json_response) {
  # Try to parse JSON
  # Sometimes AI returns text with JSON, so we extract JSON if needed
  json_match = str_extract(json_response, "\\{.*\\}")
  if (!is.na(json_match)) {
    json_response = json_match
  }
  
  # Parse JSON
  quality_data = fromJSON(json_response)
  
  # Convert to tibble
  results = tibble(
    accurate = quality_data$accurate,
    accuracy = quality_data$accuracy,
    formality = quality_data$formality,
    faithfulness = quality_data$faithfulness,
    clarity = quality_data$clarity,
    succinctness = quality_data$succinctness,
    relevance = quality_data$relevance,
    details = quality_data$details
  )
  
  return(results)
}

# 2. RUN QUALITY CONTROL ###################################

## 2.1 Create Quality Control Prompt #################################

quality_prompt = create_quality_control_prompt(report, source_data)
cat(quality_prompt)
cat("🤖 Querying AI for quality control...\n\n")

## 2.2 Query AI #################################

ai_response = query_ai_quality_control(quality_prompt, provider = "openai")

cat("📥 AI Response (raw):\n")
cat(ai_response)
cat("\n\n")

## 2.3 Parse and Display Results #################################

quality_results = parse_quality_control_results(ai_response)
cat("✅ Quality Control Results:\n")
print(quality_results)
cat("\n")

## 2.4 Calculate Overall Score #################################

# Calculate average Likert score (excluding boolean accurate)
overall_score = quality_results %>%
  select(accuracy, formality, faithfulness, clarity, succinctness, relevance) %>%
  rowMeans()

quality_results = quality_results %>%
  mutate(overall_score = round(overall_score, 2))

cat("📊 Overall Quality Score (average of Likert scales): ", overall_score, "/ 5.0\n")
cat("📊 Accuracy Check: ", ifelse(quality_results$accurate, "✅ PASS", "❌ FAIL"), "\n\n")

# 3. QUALITY CONTROL MULTIPLE REPORTS ###################################

## 3.1 Batch Quality Control Function #################################

# Function to check multiple reports
check_multiple_reports = function(reports, source_data = NULL, ai_provider = AI_PROVIDER) {
  
  cat("🔄 Performing quality control on ", length(reports), " reports...\n\n")
  
  all_results = list()
  
  for (i in 1:length(reports)) {
    cat("Checking report ", i, " of ", length(reports), "...\n")
    
    # Create prompt
    prompt = create_quality_control_prompt(reports[i], source_data)
    
    # Query AI
    tryCatch({
      response = query_ai_quality_control(prompt, provider = ai_provider)
      results = parse_quality_control_results(response)
      results = results %>% mutate(report_id = i)
      all_results[[i]] = results
    }, error = function(e) {
      cat("❌ Error checking report ", i, ": ", e$message, "\n")
    })
    
    # Small delay to avoid rate limiting
    Sys.sleep(1)
  }
  
  # Combine all results
  combined_results = bind_rows(all_results)
  
  return(combined_results)
}

## 3.2 Run Batch Quality Control (Optional) #################################

reports = read_csv("09_text_analysis/data/prompt_comparison_reports.csv") %>%
   sample_n(10)
# Uncomment to check all reports
if (length(reports) > 1) {
  batch_results = check_multiple_reports(reports$report_text, source_data, ai_provider = "openai")
  cat("\n📊 Batch Quality Control Results:\n")
  print(batch_results)
}

# View output
batch_results %>% glimpse()

batch_results %>% 
   summarize(
    accurate_pc = sum(accurate) / n(),
    accuracy_mu = mean(accuracy),
    accuracy_sd = sd(accuracy, na.rm = TRUE),
    accuracy_se = accuracy_sd / sqrt(n()),
    accuracy_lower = accuracy_mu - 1.96 * accuracy_se,
    accuracy_upper = accuracy_mu + 1.96 * accuracy_se
   ) %>%
   glimpse()

cat("✅ AI quality control complete!\n")
cat("💡 Compare these results with manual quality control (01_manual_quality_control.R) to see how AI performs.\n")
