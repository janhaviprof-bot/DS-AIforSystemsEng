![Banner Image](../docs/images/icons.png)

# README `12_end`

> Module 12 teaches a Brussels traffic pipeline: ingest realtime counts, train a model, serve predictions, and call the endpoint with an AI tool.
> This module stores data and model artifacts locally in `12_end/data/` and uses day/hour features for prediction.

---

## Table of Contents

- [Activities](#activities)
- [Readings](#readings)

---

## Activities

1. [READ: Cron Jobs and GitHub Actions for Traffic Pipelines](READ_cron_jobs.md) — Background on cron and automation
2. [ACTIVITY: Ingest Brussels Traffic Data with a Cron Job](ACTIVITY_ingest_cron.md) — Ingest Brussels realtime traffic rows on a cron
   - [`01_ingest_traffic.R`](01_ingest_traffic.R)
   - [`01_ingest_traffic.py`](01_ingest_traffic.py)
   - [`.github/workflows/12-ingest-r.yml`](../.github/workflows/12-ingest-r.yml)
   - [`.github/workflows/12-ingest-python.yml`](../.github/workflows/12-ingest-python.yml)
3. [ACTIVITY: Train a Brussels Model with a Weekly Cron Job](ACTIVITY_train_cron.md) — Train Brussels model with weekly automation
   - [`02_train_model.R`](02_train_model.R)
   - [`02_train_model.py`](02_train_model.py)
   - [`.github/workflows/12-train-r.yml`](../.github/workflows/12-train-r.yml)
   - [`.github/workflows/12-train-python.yml`](../.github/workflows/12-train-python.yml)
4. [ACTIVITY: Serve a Trained Model as a REST Endpoint](ACTIVITY_serve_model.md) — Serve `/predict?day_of_week=...&hour_of_day=...`
   - [`03_serve_model.R`](03_serve_model.R)
   - [`03_serve_model.py`](03_serve_model.py)
5. [ACTIVITY: Deploy Your Model Endpoint Online](ACTIVITY_deploy_endpoint.md) — Use standardized `manifestme/deployme/runme/testme` helpers
   - [`plumber/plumber.R`](plumber/plumber.R)
   - [`plumber/manifestme.R`](plumber/manifestme.R)
   - [`plumber/deployme.R`](plumber/deployme.R)
   - [`plumber/runme.R`](plumber/runme.R)
   - [`plumber/testme.R`](plumber/testme.R)
   - [`fastapi/main.py`](fastapi/main.py)
   - [`fastapi/manifestme.sh`](fastapi/manifestme.sh)
   - [`fastapi/deployme.sh`](fastapi/deployme.sh)
   - [`fastapi/runme.sh`](fastapi/runme.sh)
   - [`fastapi/testme.py`](fastapi/testme.py)
6. [ACTIVITY: Query Your Model Endpoint with an AI Agent](ACTIVITY_agent_query.md) — Query Brussels endpoint from tool-calling scripts
   - [`04_agent_query.R`](04_agent_query.R)
   - [`04_agent_query.py`](04_agent_query.py)
7. [LAB: Traffic Pipeline with metro_id](LAB_traffic_pipeline.md) — Adapt this pipeline structure for assigned cities

---

## Readings

- [READ: Cron Jobs and GitHub Actions for Traffic Pipelines](READ_cron_jobs.md)

---

![Footer Image](../docs/images/icons.png)

---

← 🏠 [Back to Top](#Table-of-Contents)
