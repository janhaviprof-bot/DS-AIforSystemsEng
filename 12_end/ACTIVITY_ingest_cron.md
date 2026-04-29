# 📌 ACTIVITY

## Ingest Data with a Cron Job

🕒 *Estimated Time: 10-15 minutes*

---

## ✅ Your Task

Run the Brussels ingestion script locally, then schedule it with GitHub Actions. Your script should write rows keyed by `metro_id` (not `city_id`).

### 🧱 Stage 1: Configure and run ingest locally

- [ ] Open [`01_ingest_traffic.R`](01_ingest_traffic.R) or [`01_ingest_traffic.py`](01_ingest_traffic.py).
- [ ] Confirm `METRO_ID` is set to Brussels (default `948`).
- [ ] Run the script from inside `12_end/`.
- [ ] Confirm `12_end/data/traffic.db` has rows in `traffic` for your `metro_id`.

```r
# R
db = DBI::dbConnect(RSQLite::SQLite(), "12_end/data/traffic.db")
DBI::dbReadTable(db, "traffic")
DBI::dbDisconnect(db)
```

```python
# Python
import sqlite3, pandas as pd
db = sqlite3.connect("12_end/data/traffic.db")
print(pd.read_sql("SELECT * FROM traffic", db))
db.close()
```

### 🧱 Stage 2: Schedule and verify with GitHub Actions

- [ ] Open [`.github/workflows/12-ingest-r.yml`](../.github/workflows/12-ingest-r.yml) and [`.github/workflows/12-ingest-python.yml`](../.github/workflows/12-ingest-python.yml) and identify `schedule`, `working-directory`, and commit-back steps.
- [ ] Confirm both `ingest_r` and `ingest_python` jobs run, so both language versions stay healthy.
- [ ] Commit and push your changes to GitHub.
- [ ] Run the workflow manually from **Actions**.
- [ ] Confirm the workflow updates `12_end/data/traffic.db` in a new commit.

### 🧱 Stage 3: Add dependency caching (optional but recommended)

- [ ] In Python jobs, use `actions/setup-python` with `cache: 'pip'`.
- [ ] In R jobs, use `r-lib/actions/setup-r-dependencies` to cache installed packages across runs.
- [ ] Re-run the workflow and compare execution time against an uncached run.

---

# 📤 To Submit

- For credit: one screenshot showing `traffic` rows for Brussels `metro_id` in `12_end/data/traffic.db`.

---

![](../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
