# 📌 LAB

## Create Your Own RAG AI Query

🕒 *Estimated Time: 30-45 minutes*

---

## 📋 Lab Overview

Create your own data source (text file, CSV, or SQLite database) relevant to your project, implement a search function, and build a complete RAG query workflow. This lab combines data preparation, search function implementation, and LLM integration.

---

## ✅ Your Tasks

### Task 1: Create Your Data Source

- [ ] Choose **1 data source type** based on your project needs. Eg:
  - **Text file**: Create a `.txt` file with content relevant to your project (e.g., notes, documentation, articles)
  - **CSV file**: Create a `.csv` file with structured data (e.g., project data, research findings, inventory)
  - **SQLite database**: Create a `.db` file with a `documents` table containing fields like `id`, `title`, `content`, `category`, etc.
- [ ] Ensure your data has enough content to make meaningful searches (at least 5-10 items/entries)

### Task 2: Implement Your Search Function

- [ ] Choose one of the example scripts as a template:
  - [`02_txt.py`](02_txt.py) or [`02_txt.R`](02_txt.R) for text files
  - [`03_csv.py`](03_csv.py) or [`03_csv.R`](03_csv.R) for CSV files
  - [`04_sqlite.py`](04_sqlite.py) or [`04_sqlite.R`](04_sqlite.R) for SQLite databases
  - [`05_embed.py`](05_embed.py) or [`05_embed.R`](05_embed.R) for Vector Embedding + Semantic Search (Industry Standard)
- [ ] Adapt the script's search function to match your data structure and needs:
- [ ] Test your search function with a sample query.

### Task 3: Build Your RAG Query Workflow

- [ ] Set up the configuration (MODEL, PORT, OLLAMA_HOST, document path)
- [ ] Add in your search function
- [ ] Pass your results as a JSON to the LLM
- [ ] Design a system prompt (role) that instructs the LLM on how to process your data
- [ ] Test your complete workflow with multiple queries, and fix your prompt if necessary


---

## 📤 To Submit

- For credit: Submit:
  1. Your complete RAG workflow script (Python or R)
  2. Screenshot showing the output from running your RAG query
  3. Brief explanation (3-4 sentences) describing:
     - What data source you created and why
     - How your search function works
     - What your system prompt instructs the LLM to do

---

![](../docs/images/icons.png)

---

← 🏠 [Back to Top](#LAB)
