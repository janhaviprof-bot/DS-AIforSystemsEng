# 📌 MIDTERM

## DL Challenge: AI-Powered Database Pipeline

🕒 *Estimated Time: 1 week*

---

## 📋 Lab Overview

Design, implement, and deploy a multi-part AI-powered system that demonstrates your ability to handle complexity and make AI do something interesting **with a database**. Your system must integrate a **Supabase PostgreSQL database**, a **REST API**, a **dashboard app**, and an **AI model** into a working, deployed application.

**Challenge**: Can you handle complexity? Can you use Cursor to learn on the fly? Can you make an AI do something interesting from a database?

**Timeline**: 
- Prompt released: **March 2, 2026**
- Due date: **March 9, 2026 at 9:00 AM**

**Team Size**: Work individually or in teams of 3-5 students.

---

## ✅ Your Tasks

### Task 1: Design Your System

- [ ] **Solve the problem described in [MIDTERM_DL_challenge_prompts.md](MIDTERM_DL_challenge_prompts.md)**
- [ ] Design a pipeline that integrates:
  - **Supabase database** (data storage)
  - **REST API** (data access layer)
  - **Dashboard app** (user interface)
  - **AI model** (intelligent processing)
- [ ] Define what your AI will do with the database data (e.g., generate summaries, make recommendations, classify data, answer questions)
   - Note: **Core objective is to get all parts talking to each other successfully.**

### Task 2: Build Your Components

- [ ] Set up your **Supabase database** with appropriate schema and sample data
- [ ] Build a **REST API** (using Plumber in R or FastAPI/Flask in Python) that queries your database
- [ ] Create a **dashboard app** (Shiny in R or in Python) that connects to your API
- [ ] Integrate an **AI model** (OpenAI or Ollama Cloud) that processes data from your database to provide meaningful insights

### Task 3: Deploy Your System

- [ ] Deploy your complete system to **DigitalOcean** or **Posit Connect**
- [ ] Ensure all components are accessible and working together
- [ ] Test your deployed system with sample data

### Task 4: Document Your Work

- [ ] Create a **README** explaining your system architecture and how to use it
- [ ] Document your database schema and data structure
- [ ] Provide **2-3 test datasets** that demonstrate your system's functionality
- [ ] Include a **codebook** describing your data files and variables
- [ ] Make your code **reproducible** and share it on a public GitHub repository

---

## 💡 Tips and Resources

- **Training materials**: You'll receive training videos and GitHub folders with examples to guide your work
- **Scope**: Keep your scope narrow and focused. A small system that works is better than a large one that doesn't
- **Delegation**: If working in a team, divide responsibilities (database, API, dashboard, AI integration, deployment)
- **Use Cursor**: AI-assisted coding with Cursor is encouraged. 
- **Use MCP tools!**: Supabase has a very effective MCP server Cursor can access.
- **Focus on the pipeline**: This challenge is more focused than the hackathon—you must build a specific style of pipeline (database → API → dashboard → AI), but what you build within that structure is up to you

---

## 🏆 Evaluation Criteria

Your project will receive a score of **0 to 100** based on:

### 🧱 Tool Implementation (50 pts)
- **(10 pts)** Did you host and connect to a Supabase database in your pipeline?
- **(10 pts)** Did you serve an API to do some kind of data processing/handling in your pipeline?
- **(10 pts)** Did you query an AI model to solve the prompt problem in your pipeline?
- **(10 pts)** Did you serve a Shiny App to deliver results to a user in your pipeline?
- **(10 pts)** An effective, working tool — does it run and deploy?

### 🧭 Tool Design (15 pts)
- **(5 pts)** System architecture follows the required pipeline structure (database → API → dashboard → AI)
- **(5 pts)** Clear user and use case in mind
- **(5 pts)** Minimal, reasonable number of inputs or requirements from the user

### 📑 Tool Documentation (35 pts)
- **(10 pts)** 2–3 accurate, working test executions
- **(10 pts)** Clear demonstration of the tool using the test executions
- **(5 pts)** Excellent, easy-to-follow documentation for the tool — how each function works, inputs, parameters, etc.
- **(5 pts)** A codebook and README for your pipeline files, describing each file and variable and background needed to collect or use the data
- **(5 pts)** Fully reproducible code, posted publicly to a GitHub repository

---

## 📤 To Submit

- For credit: Submit a link to your **public GitHub repository** containing:
  - All code (database schema, API, dashboard, AI integration)
  - README with system architecture and usage instructions
  - Codebook describing your data
  - Link to your **deployed application** (DigitalOcean or Posit Connect)
  - Test demonstration examples

**Due**: March 9, 2026 at 9:00 AM

---

![](../../docs/prep/icons.png)

---

← 🏠 [Back to Top](#LAB)
