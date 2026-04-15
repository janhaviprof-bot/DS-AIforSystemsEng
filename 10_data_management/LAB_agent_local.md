# 📌 LAB

## Run an Autonomous Agent Locally (Python or R)

🕒 *Estimated Time: 10–15 minutes*

---

## 📋 Lab Overview

You will install dependencies, configure **Ollama Cloud**, and call the **disaster situational brief** agent on your machine using plain **HTTP JSON** (no Slack). The same API exists in two implementations—pick **one**:

| Track | Folder | Stack |
|--------|--------|--------|
| **Python** | [`agentpy/`](agentpy/) | **FastAPI** + uvicorn |
| **R** | [`agentr/`](agentr/) | **Plumber** + **httr2** + **reticulate** (CrewAI **SerperDevTool** for search) |

Endpoints are the same: **`GET /health`**, **`POST /hooks/agent`**, **`POST /hooks/control`** on **`http://127.0.0.1:8000`** (unless you change the port). Use **`curl`**, **[Postman](https://www.postman.com/)**, or any HTTP client.

---

## ✅ Your Task

### 🧱 Stage 1: Environment

- [ ] **Choose Python or R** (one track for this activity).
  - [ ] **Python:** In a virtual environment, from **`agentpy/`**, run **`pip install -r requirements.txt`**.
  - [ ] **R:** Install CRAN packages **`plumber`**, **`jsonlite`**, **`httr2`**, **`reticulate`**; configure a Python environment with **`crewai_tools`** (see **[`agentr/README.md`](agentr/README.md)** — **`requirements.txt`** and **`RETICULATE_PYTHON`**).
- [ ] Copy **[`agentpy/.env.example`](agentpy/.env.example)** or **[`agentr/.env.example`](agentr/.env.example)** to **`.env`** inside that same folder (**`agentpy/`** or **`agentr/`**) and add your **`OLLAMA_API_KEY`** from [ollama.com](https://ollama.com) (keep **`.env`** gitignored).
- [ ] Confirm **`OLLAMA_HOST`** and **`OLLAMA_MODEL`** match the course default (**`nemotron-3-nano:30b-cloud`**) unless your instructor says otherwise.
- [ ] Register for a **`Serper.dev` API Key**! This agent uses the `SerperDevTool` tool from the **`crewai_tools`** library, which lets it search the internet! Signup for an account at [serper.dev/signup](https://serper.dev/signup), create an API key, and add it to your `.env` file as `SERPER_API_KEY`.
  - <img width="1548" height="990" alt="image" src="https://github.com/user-attachments/assets/fd784ff8-2354-4373-b65d-2c7fa59393dd" />

### 🧱 Stage 2: Start the API

- [ ] **Python:** From **`agentpy/`**, start the server: **`python -m uvicorn app.api:app --host 0.0.0.0 --port 8000`**, or **`./runme.sh`** (see **[`agentpy/README.md`](agentpy/README.md)**).
- [ ] **R:** From the **repository root** (**`dsai`**), run **`Rscript 10_data_management/agentr/runme.R`** or **`source("10_data_management/agentr/runme.R")`** (see **[`agentr/README.md`](agentr/README.md)**).
- [ ] Open **`http://127.0.0.1:8000/health`** in a browser and confirm you see **`"ok": true`**.
  - <img width="452" height="128" alt="image" src="https://github.com/user-attachments/assets/f61a194f-41b1-4763-89c6-ab3d7cff2424" />
- [ ] Open **`http://127.0.0.1:8000/docs`** in a browser and peruse the Swagger UI documentation for the app! If successful, you will see this!
  - <img width="1317" height="1296" alt="image" src="https://github.com/user-attachments/assets/572fca19-d2f9-4457-aa5b-0982eb26077c" />
- [ ] Optional: after a brief, open **`logs/agent.log`** under **`agentpy/`** or **`agentr/`** and confirm turn-by-turn log lines (see the README for that folder if logging is disabled).
  - <img width="1678" height="785" alt="image" src="https://github.com/user-attachments/assets/1a54955e-0745-4c8e-9967-adbef953a6b3" />
 



### 🧱 Stage 3: Send a task

- [ ] **`POST`** to **`http://127.0.0.1:8000/hooks/agent`** with JSON **`{"task": "Your disaster snapshot or follow-up (incident name, area, time window if relevant)"}`** (Postman or **`curl`**).
- [ ] Read the JSON response: note **`status`**, **`turns_used`**, **`turn_cap`**, and **`session_id`**. If **`status`** is **`paused_for_human`**, the model hit the turn cap for that request—use **`resume_token`** in a follow-up request (see **[`agentpy/README.md`](agentpy/README.md)** or **[`agentr/README.md`](agentr/README.md)**). Optionally send **`max_turns`** (≤ server max).

---

# 📤 To Submit

- Screenshot of a successful **`/hooks/agent`** response (or terminal output) showing **`status`** and **`reply`**.
- One sentence: what does **`END_BRIEF`** in **`AGENT.md`** (in **`agentpy/`** or **`agentr/`**, depending on your track) signal?

---

![](../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
