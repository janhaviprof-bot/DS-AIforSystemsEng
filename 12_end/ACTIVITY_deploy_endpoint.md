# 📌 ACTIVITY (OPTIONAL)

## Deploy Model Endpoint Online

🕒 *Estimated Time: 10-15 minutes*

---

## ✅ Your Task

Deploy your local prediction endpoint so it serves `/predict?day_of_week=...&hour_of_day=...` from your latest framework-specific model (`data/modelr.json` for Plumber or `data/modelpy.json` for FastAPI).

### 🧱 Stage 1: Choose one deployment path

#### Option A: Posit Connect (R — Plumber)

Use this option if you prefer R or already have a Posit Connect account from earlier modules.

Files:
- [`plumber/plumber.R`](plumber/plumber.R)
- [`plumber/manifestme.R`](plumber/manifestme.R)
- [`plumber/deployme.R`](plumber/deployme.R)
- [`plumber/runme.R`](plumber/runme.R)
- [`plumber/testme.R`](plumber/testme.R)

Steps:

- [ ] Run [`plumber/manifestme.R`](plumber/manifestme.R) to generate a manifest.
- [ ] Run [`plumber/deployme.R`](plumber/deployme.R) to deploy to Posit Connect.
- [ ] For local testing, run [`plumber/runme.R`](plumber/runme.R).
- [ ] Smoke-test with [`plumber/testme.R`](plumber/testme.R).
- [ ] You can still deploy manually in RStudio if preferred:

```r
rsconnect::deployAPI(
  api       = "12_end",
  appTitle  = "traffic-model-endpoint"
)
```

- [ ] Wait for the deployment to complete. Posit Connect handles the R environment automatically — no Docker required.
- [ ] Copy the live URL from the deployment output (e.g. `https://connect.example.com/traffic-model-endpoint`).


#### Option B: Posit Connect (Python — FastAPI)

Use this option if you prefer Python and want to deploy the FastAPI version to Posit Connect.

Files:
- [`fastapi/main.py`](fastapi/main.py)
- [`fastapi/manifestme.sh`](fastapi/manifestme.sh)
- [`fastapi/deployme.sh`](fastapi/deployme.sh)
- [`fastapi/runme.sh`](fastapi/runme.sh)
- [`fastapi/testme.py`](fastapi/testme.py)

Steps:

- [ ] Run `bash 12_end/fastapi/manifestme.sh` to generate a manifest.
- [ ] Run `bash 12_end/fastapi/deployme.sh` to deploy to Posit Connect.
- [ ] For local testing, run `bash 12_end/fastapi/runme.sh`.
- [ ] Smoke-test with `python 12_end/fastapi/testme.py`.

### 🧱 Stage 2: Verify your live endpoint

Both options end at the same place: a live URL that responds to GET requests.

- [ ] Test your live endpoint in a browser or with curl:

```bash
curl "https://your-live-url/predict?day_of_week=1&hour_of_day=8"
```

Expected response:
```json
{"predicted_vehicle_count": 1423.7}
```

- [ ] Save your live endpoint URL — you will paste it into [`04_agent_query.R`](04_agent_query.R) or [`04_agent_query.py`](04_agent_query.py) in the next activity.

---

# 📤 To Submit

- For credit: one screenshot of a successful live `/predict?day_of_week=1&hour_of_day=8` response.

---

![](../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
