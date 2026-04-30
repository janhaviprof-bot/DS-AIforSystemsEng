# 📌 ACTIVITY (OPTIONAL)

## Deploy Model Endpoint Online

🕒 *Estimated Time: 10-15 minutes*

---

## ✅ Your Task

Deploy your local prediction endpoint so it serves `/predict?day_of_week=...&hour_of_day=...` from your latest framework-specific model (`data/modelr.json` for Plumber or `data/modelpy.json` for FastAPI).

### 🧱 Stage 1: Choose one deployment path

#### Option A: Posit Connect (R — Plumber)

Use this option if you prefer R or already have a Posit Connect account from earlier modules.

Files (under [`12_end/03_plumber/`](03_plumber/)):

- [`03_plumber/plumber.R`](03_plumber/plumber.R)
- [`03_plumber/manifestme.R`](03_plumber/manifestme.R)
- [`03_plumber/deployme.R`](03_plumber/deployme.R)
- [`03_plumber/runme.R`](03_plumber/runme.R)
- [`03_plumber/testme.R`](03_plumber/testme.R)

Steps:

- [ ] From the repo root, run [`03_plumber/manifestme.R`](03_plumber/manifestme.R) (or open it in RStudio and source it) to generate a manifest.
- [ ] Configure [`03_plumber/.env`](03_plumber/.env.example) from [`.env.example`](03_plumber/.env.example), then run [`03_plumber/deployme.R`](03_plumber/deployme.R) to deploy to Posit Connect. Adjust `SERVER_NAME` in `deployme.R` if your Connect server was registered under a different name.
- [ ] For local testing, run [`03_plumber/runme.R`](03_plumber/runme.R).
- [ ] Smoke-test with [`03_plumber/testme.R`](03_plumber/testme.R).
- [ ] You can still deploy manually in RStudio if preferred:

```r
rsconnect::deployAPI(
  api       = "12_end",
  appTitle  = "traffic-model-endpoint"
)
```

- [ ] Wait for the deployment to complete. Posit Connect handles the R environment automatically — no Docker required.
- [ ] Copy the live URL from the deployment output (for example `https://connect.example.com/content/...`).


#### Option B: Posit Connect (Python — FastAPI)

Use this option if you prefer Python and want to deploy the FastAPI version to Posit Connect.

Files (under [`12_end/03_fastapi/`](03_fastapi/)):

- [`03_fastapi/main.py`](03_fastapi/main.py)
- [`03_fastapi/manifestme.sh`](03_fastapi/manifestme.sh) or [`03_fastapi/manifestme.ps1`](03_fastapi/manifestme.ps1) (Windows)
- [`03_fastapi/deployme.sh`](03_fastapi/deployme.sh) or [`03_fastapi/deployme.ps1`](03_fastapi/deployme.ps1) (Windows)
- [`03_fastapi/runme.sh`](03_fastapi/runme.sh)
- [`03_fastapi/testme.py`](03_fastapi/testme.py)

Steps:

- [ ] Copy [`03_fastapi/.env.example`](03_fastapi/.env.example) to `03_fastapi/.env` and set **`CONNECT_SERVER`** (full `https://...` Posit Connect base URL) and **`CONNECT_API_KEY`**. On Windows PowerShell, a `.env` file is **not** loaded automatically — use **`deployme.ps1`**, which loads it, or set `$env:CONNECT_SERVER` / `$env:CONNECT_API_KEY` yourself before `rsconnect deploy`.
- [ ] Generate a manifest: from repo root, **`bash 12_end/03_fastapi/manifestme.sh`** (Git Bash or macOS/Linux), **or** `powershell -NoProfile -ExecutionPolicy Bypass -File 12_end/03_fastapi/manifestme.ps1`. These scripts copy `12_end/data/modelpy.json` and `12_end/data/validationpy.json` into `03_fastapi/data/` so Posit Connect bundles the trained model (without them, the app crashes at import and `rsconnect` verification fails).
- [ ] Deploy: **`bash 12_end/03_fastapi/deployme.sh`** **or** `powershell -NoProfile -ExecutionPolicy Bypass -File 12_end/03_fastapi/deployme.ps1`. If `bash` on Windows routes to a broken WSL install, use Git Bash or the `.ps1` scripts instead.
- [ ] For local testing, from `12_end/03_fastapi`: `python -m uvicorn main:app --host 127.0.0.1 --port 8000` (same as [`runme.sh`](03_fastapi/runme.sh)).
- [ ] Smoke-test: from repo root, `python 12_end/03_fastapi/testme.py` (install `requests` and `python-dotenv` if needed). For a deployed URL, set **`API_PUBLIC_URL`** in `.env` to that URL before running `testme.py`.

### 🧱 Stage 2: Verify your live endpoint

Both options end at the same place: a live URL that responds to GET requests.

- [ ] Test your live endpoint in a browser or with curl:

```bash
curl "https://your-live-url/predict?day_of_week=1&hour_of_day=8"
```

Expected response includes **`predicted_vehicle_count`** (and may include `standard_error` fields from the FastAPI app).

- [ ] Save your live endpoint URL — you will paste it into [`04_agent_query.R`](04_agent_query.R) or [`04_agent_query.py`](04_agent_query.py) in the next activity.

---

# 📤 To Submit

- For credit: one screenshot of a successful live `/predict?day_of_week=1&hour_of_day=8` response.

---

![](../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
