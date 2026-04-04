# 📌 ACTIVITY

## Run the Autonomous Agent Locally (Python or R)

🕒 *Estimated Time: 10–15 minutes*

---

## 📋 Overview

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
- [ ] Copy **[`agentpy/.env.example`](agentpy/.env.example)** or **[`agentr/.env.example`](agentr/.env.example)** to **`.env`** inside that same folder (**`agentpy/`** or **`agentr/`**) and add your **`OLLAMA_API_KEY`** from [ollama.com](https://ollama.com) (keep **`.env`** gitignored).
- [ ] Confirm **`OLLAMA_HOST`** and **`OLLAMA_MODEL`** match the course default (**`nemotron-3-nano:30b-cloud`**) unless your instructor says otherwise.
- [ ] **Python:** In a virtual environment, from **`agentpy/`**, run **`pip install -r requirements.txt`**.
- [ ] **R:** Install CRAN packages **`plumber`**, **`jsonlite`**, **`httr2`**, **`reticulate`**; configure a Python environment with **`crewai_tools`** (see **[`agentr/README.md`](agentr/README.md)** — **`requirements.txt`** and **`RETICULATE_PYTHON`**).

### 🧱 Stage 2: Start the API

- [ ] **Python:** From **`agentpy/`**, start the server: **`python -m uvicorn app.api:app --host 0.0.0.0 --port 8000`**, or **`./runme.sh`** (see **[`agentpy/README.md`](agentpy/README.md)**).
- [ ] **R:** From the **repository root** (**`dsai`**), run **`Rscript 10_data_management/agentr/runme.R`** or **`source("10_data_management/agentr/runme.R")`** (see **[`agentr/README.md`](agentr/README.md)**).
- [ ] Open **`http://127.0.0.1:8000/health`** in a browser and confirm you see **`"ok": true`**.
- [ ] Optional: after a brief, open **`logs/agent.log`** under **`agentpy/`** or **`agentr/`** and confirm turn-by-turn log lines (see the README for that folder if logging is disabled).

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
