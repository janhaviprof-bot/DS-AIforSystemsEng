# 05_reporting.R
# Save AI Report in Multiple Formats
# Pairs with 05_reporting.py
# Tim Fraser

# This script demonstrates how to save AI-generated reports in different formats:
# .txt, .md, .html, and .docx. Students will learn how to format and write
# LLM output to various file types for different use cases.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

# If you haven't already, install required packages:
# install.packages(c("readr", "rmarkdown", "officer"))

library(readr)     # for writing text files
library(rmarkdown) # for generating HTML reports
library(officer)   # for creating Word documents

## 0.2 Mock LLM Output #########################

# Simulate an AI response object
# In a real script, this would come from your LLM API call
mock_llm_response = list(
  response = "# Data Analysis Report

## Summary
The dataset contains 150 records with 3 key metrics showing positive trends.

## Key Findings
- Metric A increased by 15% over the period
- Metric B remained stable at 42 units
- Metric C showed significant variation

## Recommendations
Consider further investigation into Metric C variations."
)

# Extract the text content
report_text = mock_llm_response$response

# 1. SAVE AS PLAIN TEXT (.txt) ###################################

# Use readr::write_lines for simple text file writing
# Simple and universal format
write_lines(report_text, "03_query_ai/05_reporting_report.txt")

cat("✅ Saved 05_reporting_report.txt\n")

# 2. SAVE AS MARKDOWN (.md) ###################################

# Markdown files are great for GitHub and documentation
# The content is already in markdown format, so we just write it
write_lines(report_text, "03_query_ai/05_reporting_report.md")

cat("✅ Saved 05_reporting_report.md\n")

# 3. SAVE AS HTML (.html) ###################################

# Create a temporary R Markdown file
temp_rmd = "03_query_ai/temp_report.Rmd"
write_lines(c("---", "output: html_document", "---", "", report_text), temp_rmd)

# Render to HTML
render(temp_rmd, output_file = "05_reporting_report.html", quiet = TRUE)

# Clean up temporary file
file.remove(temp_rmd)

cat("✅ Saved 05_reporting_report.html\n")

# 4. SAVE AS WORD DOCUMENT (.docx) ###################################

# Create a Word document using officer package
doc = read_docx()

# Split content by lines and add to document
# Handle markdown headers and formatting
lines = strsplit(report_text, "\n")[[1]]

for (line in lines) {
  if (startsWith(line, "# ")) {
    # Main heading
    doc = body_add_par(doc, substring(line, 3), style = "heading 1")
  } else if (startsWith(line, "## ")) {
    # Subheading
    doc = body_add_par(doc, substring(line, 4), style = "heading 2")
  } else if (startsWith(line, "- ")) {
    # Bullet point
    doc = body_add_par(doc, substring(line, 3), style = "List Bullet")
  } else if (nchar(trimws(line)) > 0) {
    # Regular paragraph
    doc = body_add_par(doc, line)
  }
}

print(doc, target = "03_query_ai/05_reporting_report.docx")

cat("✅ Saved 05_reporting_report.docx\n")
cat("\n✅ All report formats saved successfully!\n")
