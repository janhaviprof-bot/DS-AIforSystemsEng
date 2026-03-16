### Multi-Agent Travel Itinerary Workflow (Macro View)

This lab demonstrates a **four-agent workflow** that builds a weather-aware one-day itinerary for a city using only HTTP APIs.

The agents and data flow are:

- **Agent 1 – Attractions Agent**
  - **Input**: Raw JSON from the OpenTripMap API for a given city (via `get_city_attractions()`).
  - **Role**: Clean and compress the attractions data into a concise JSON:
    - `city`
    - `attractions[]` with `name`, `category`, `indoor`, `short_description`
  - **Output**: Machine-readable attractions JSON for the itinerary agent.

- **Agent 2 – Weather Agent**
  - **Input**: Raw JSON from the Open-Meteo APIs for the same city (via `get_city_weather()`).
  - **Role**: Summarize the day’s weather into three time blocks:
    - `morning`, `afternoon`, `evening` with `temp_c`, `conditions`, `precipitation`
  - **Output**: Compact weather JSON plus a one- or two-sentence daily summary.

- **Agent 3 – Weather-Aware Itinerary Planner**
  - **Input**: Combined JSON:
    - `city`
    - `attractions[]` from Agent 1
    - `weather` from Agent 2
  - **Role**: Design a **one-day plan** that:
    - Uses only the listed attractions
    - Organizes activities into:
      - `### Morning`
      - `### Afternoon`
      - `### Evening`
    - Takes weather into account when choosing indoor vs outdoor options
  - **Output**: Human-readable markdown itinerary:
    - `## One-Day Plan for <city> (Weather-Aware)`
    - Three sections with 1–2 concrete activities each.

- **Agent 4 – Timed To-Do Scheduler**
  - **Input**:
    - The markdown itinerary from Agent 3
    - Full attractions list
    - A subset of places likely suitable for meals (meal places)
  - **Role**: Convert the itinerary into a **timed day schedule**:
    - Preserve the activities from the itinerary
    - Add **breakfast, lunch, and dinner** at plausible locations (API-backed when possible, otherwise generic “near \<attraction\>” options)
    - Assign realistic time ranges to each item
  - **Output**: A markdown “timed to-do list” suitable to use as a day plan checklist.

### Orchestration Overview

At a high level, the Python script:

1. **Calls APIs**:
   - `get_city_attractions(city)` → OpenTripMap
   - `get_city_weather(city)` → Open-Meteo
2. **Runs Agents 1 and 2** on the raw JSON to clean and summarize the data.
3. **Runs Agent 3** with a combined JSON payload to produce a weather-aware itinerary.
4. **Runs Agent 4** with the itinerary plus place data to produce a timed to-do list.

All calls to the language model go through `agent_run(...)` in `functions.py`, and rules for each agent’s behavior are stored in `lab_rules.yaml` for clarity and reuse.

