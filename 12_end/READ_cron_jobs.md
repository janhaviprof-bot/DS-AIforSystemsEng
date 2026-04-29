# 📌 READ

## Cron Jobs and GitHub Actions for Singapore Traffic

🕒 *Estimated Time: 10 minutes*

---

## What is a Cron Job?

A cron job is a scheduled task that runs automatically at set intervals — no manual trigger needed. You define *when* it runs and *what* it runs, then it executes in the background on a server.

Common uses:
- Nightly data pulls from a traffic or weather API
- Weekly model retraining on fresh data
- Daily database cleanup or archival

---

## Cron Syntax

A cron schedule is five fields separated by spaces:

```
* * * * *
│ │ │ │ └── day of week (0=Sun, 6=Sat)
│ │ │ └──── month (1–12)
│ │ └────── day of month (1–31)
│ └──────── hour (0–23)
└────────── minute (0–59)
```

Examples:

| Schedule | Meaning |
|---|---|
| `0 0 * * *` | Daily at midnight UTC |
| `0 8 * * 1` | Every Monday at 8am UTC |
| `*/15 * * * *` | Every 15 minutes |

Use [crontab.guru](https://crontab.guru) to test your expressions.

---

## GitHub Actions as a Cron Runner

GitHub Actions workflows can act as cron runners. Add a `schedule:` trigger to any `.yml` workflow file in `.github/workflows/` and GitHub will run it on your chosen schedule — on GitHub's servers, not yours.

```yaml
on:
  schedule:
    - cron: '0 6 * * *'   # daily at 6am UTC
  workflow_dispatch:        # also allow manual trigger
```

Key points:
- Free on public repos; counts against minutes on private repos
- A ~15-minute delay from the scheduled time is normal on the free tier
- Use `workflow_dispatch:` alongside `schedule:` so you can test it manually without waiting

---

## Why Combine Cron + REST Endpoints?

Cron jobs and REST endpoints play complementary roles in a data pipeline:

```
data.gov.sg (Singapore) → ingest cron → SQLite/Supabase table with metro_id → train cron → modelr.json/modelpy.json → REST endpoint → agent
```

- **Ingest cron**: runs daily, pulls Singapore annual traffic rows, writes `metro_id`, `observed_at`, and `vehicle_count`
- **Train cron**: runs weekly, reads one metro's rows and trains a simple year-based model
- **REST endpoint**: runs always, loads `modelr.json` (R) or `modelpy.json` (Python), returns predictions from `year`
- **Agent**: calls `/predict?year=...` as a tool

This separation keeps each piece simple and independently replaceable.

---

![](../docs/images/icons.png)

---

← 🏠 [Back to Top](#READ)
