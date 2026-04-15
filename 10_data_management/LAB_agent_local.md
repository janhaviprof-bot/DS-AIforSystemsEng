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

- [ ] **`POST`** to **`http://127.0.0.1:8000/hooks/agent`** with JSON **`{"task": "Your disaster snapshot or follow-up (incident name, area, time window if relevant)"}`** (Use the Swagger UI or a **`curl`** request).
   - For example, here's my Swagger UI request...
<img width="1314" height="1476" alt="image" src="https://github.com/user-attachments/assets/ed157718-b6c2-4bc8-b775-bf85e123806b" />

   - Here's the curl request it generated:

```curl
curl -X 'POST' \
  'http://localhost:8000/hooks/agent' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "task": "Situational snapshot: Nevada Earthquake near Carson City, focus on damage, injuries, outages and state EOC messaging in the last 72 hours.",
  "max_turns": 6
}'
```
   - And here's my result!
<img width="1246" height="1397" alt="image" src="https://github.com/user-attachments/assets/1d29b0e0-0226-4fb1-b811-6ce5ccc5ba36" />


- [ ] Read the JSON response: note **`status`**, **`turns_used`**, **`turn_cap`**, and **`session_id`**.
   - If **`status`** is **`paused_for_human`**, the model hit the turn cap for that request—use **`resume_token`** in a follow-up request (see **[`agentpy/README.md`](agentpy/README.md)** or **[`agentr/README.md`](agentr/README.md)**). Optionally send **`max_turns`** (≤ server max).
   - For example, here's my JSON response!

```json
{
  "status": "ok",
  "reply": "## Question restatement\n\n- **Disaster name / event:** Nevada earthquake near Carson City  \n- **Geographic focus:** Rural Nevada/East of Carson City, with some references to Carson City itself  \n- **Time window:** Damage, injuries, outages, and state Emergency Operations Center (EOC) messaging reported in the **last 72 hours** (i.e., since roughly 3 days ago)  \n\n---\n\n## Key points (3 bullets max)\n\n- The USGS recorded a **5.7 magnitude earthquake** east of Carson City on **Monday** (the Monday before the current reporting day), with **minor structural damage and rockfall** reported near the epicenter; no **civilian injuries** have been officially confirmed so far.  \n- Reports of **power and communications outages** are patchy; isolated utility crews noted **brief service interruptions** in a few rural communities, but no widespread outages have been documented across the region.  \n- The **state EOC** issued public statements **via social media and local news outlets** confirming the quake, directing residents to stay away from damaged structures, and monitoring for **aftershocks**; no formal shelter activations have been announced.\n\n---\n\n## References\n\n1. [A 5.7‑earthquake jolts rural Nevada near Carson City causing some damage (WCCO)](https://www.wral.com/news/ap/03540-a-5-7-earthquake-jolts-rural-nevada-near-carson-city-causing-some-damage/)  \n2. [A 5.7‑earthquake jolts rural Nevada near Carson City causing some damage (AOL)](https://www.aol.com/articles/5-7-earthquake-jolts-rural-030053133.html)  \n3. [A 5.7 earthquake jolts rural Nevada near Carson City with damage reported (KTAR)](https://ktar.com/national-news/a-5-7-earthquake-jolts-rural-nevada-near-carson-city-with-damage-reported/5847317/)  \n4. [YouTube – Nevada Officials Report Damage After 5.7‑Magnitude Earthquake](https://www.youtube.com/watch?v=KcIV8Vhyyjw)  \n5. [St. Albert Gazette – 5.7‑earthquake jolts rural Nevada near Carson City with damage reported](https://www.stalbertgazette.com/weather-news/a-57-earthquake-jolts-rural-nevada-near-carson-city-with-damage-reported-12138259)  \n6. [NY Times Interactive Quake Tracker – Nevada](https://www.nytimes.com/interactive/2026/04/13/us/quake-tracker-nevada.html)  \n7. [EarthquakeTrack – Real‑time earthquake data for Nevada](https://earthquaketrack.com/)  \n8. [Facebook – Fox Weather post on the 5.5‑magnitude quake shaking shelves](https://www.facebook.com/FoxWeather/posts/see-it-a-55-magnitude-earthquake-knocked-products-from-their-shelves-to-the-floo/984025140804447/)  \n\n---\n\nConfidence: **medium** — multiple reputable news outlets and official state channels were found, but the material is largely **aggregate** and does not disaggregate damage or outage details down to specific neighborhoods or precise mile‑by‑mile utility maps.",
  "turns_used": 2,
  "turn_cap": 6,
  "session_id": "63102180-8c9e-4150-8457-d34b533226e7",
  "prefetch_search_used": true,
  "forced_tool_round": true,
  "min_completion_turns": 2,
  "resume_token": null
}
```

  - Notice also that I customized (with Cursor's help) the Swagger UI's `Descriptions` of response codes. This makes it a lot easier for humans to interpret and debug API response errors. 
   <img width="1283" height="1188" alt="image" src="https://github.com/user-attachments/assets/21d032cc-bd09-4a92-b260-1a9ee5ceae8c" />



---

# 📤 To Submit

- Screenshot of a successful **`/hooks/agent`** response (or terminal output) showing **`status`** and **`reply`**.
- One sentence: what does **`END_BRIEF`** signal in **`AGENT.md`** (in **`agentpy/`** or **`agentr/`**, depending on your track)?

---

![](../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
