# MIDTERM DL Challenge — Prompt

*Your solution must satisfy all requirements in [MIDTERM_DL_challenge.md](./MIDTERM_DL_challenge.md), including the pipeline: **Supabase database → REST API → dashboard → AI**. The tool must **work** end-to-end and be deployable.*

---

## DL Challenge 2026: City Congestion Tracker

A city transportation authority needs to see where congestion is building and how it changes over time — but they don’t have a single system that stores congestion data, serves it through an API, and turns it into plain-language insights. 

Your job is to build a **congestion-tracking system** that (1) stores congestion-level data in a **Supabase** database, (2) exposes it through a **REST API** (e.g., by location, time window, or severity), (3) provides a **dashboard** where a user can explore current or historical congestion and request a summary, and (4) uses an **AI model** (OpenAI or Ollama Cloud) to turn a slice of that data into a short, actionable summary (e.g., which areas are worst now, how today compares to usual, what to watch next, which roads to avoid, etc.). 

**You do not need real data.** You are strongly encouraged to use **synthetic data** you generate (e.g., script-generated records for intersections, segments, or zones with timestamps and congestion levels, etc.). The system must work with your data and meet all midterm criteria.

**Example queries your system could support:**

- “Which intersections (or segments/zones) are currently showing the highest congestion?”

- “Given the data in the database for the last 7 days, summarize how congestion typically varies by time of day.”

- “How does congestion right now (or for a selected period) compare to the historical pattern — better, worse, or similar?”

**Suggested data sources**

| Type | Options |
|------|--------|
| **DATA (preferred)** | **Synthetic data you create**: e.g., a script or CSV with rows like `location_id`, `timestamp`, `congestion_level` (or speed, delay, volume). Use a minimal schema (e.g., one main table for readings, optionally one for locations). Faker (Python), `data.frame` in R, or hand-crafted CSVs are all fine. |
| **API (optional)** | If you want to try real feeds later: GTFS Realtime, MTA API, or open traffic datasets — but **synthetic data is sufficient** for the midterm. (*Don't spend too much time trying to use real data feeds at the expense of the greater goal of the project!*) |
| **AI** | OpenAI API or Ollama Cloud. Send a compact summary of the queried data (counts, top locations, simple stats) and ask for a short narrative summary or comparison. |
---

**Suggestions:** Keep it small but interconnected — one or two tables, clear filters in the API, one main AI summary flow, and all four components (database, API, dashboard, AI) working together.
