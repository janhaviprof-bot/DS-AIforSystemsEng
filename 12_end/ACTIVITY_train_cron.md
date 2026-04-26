# 📌 ACTIVITY

## Train a Brussels Model with a Weekly Cron Job

🕒 *Estimated Time: 10-15 minutes*

---

## ✅ Your Task

Train an XGBoost model using Brussels rows for one `metro_id`, then run weekly retraining in GitHub Actions.

### 🧱 Stage 1: Train locally

- [ ] Open [`02_train_model.R`](02_train_model.R) or [`02_train_model.py`](02_train_model.py).
- [ ] Confirm `METRO_ID` is set to Brussels (default `948`).
- [ ] Run the script from `12_end/`.
- [ ] Confirm `data/model.json` is created and RMSE is printed.

```
Model saved to data/model.json
Training RMSE: 142.35
```

### 🧱 Stage 2: Automate weekly retraining

- [ ] Open [`.github/workflows/12-train-r.yml`](../.github/workflows/12-train-r.yml) and [`.github/workflows/12-train-python.yml`](../.github/workflows/12-train-python.yml) and inspect the weekly cron schedule.
- [ ] Confirm both `train_r` and `train_python` jobs run, so both model pipelines stay aligned.
- [ ] Trigger the workflow manually from **Actions**.
- [ ] Download the model artifacts and confirm both include `data/model.json`.

### 🧱 Stage 3: Add dependency caching (optional but recommended)

- [ ] In Python jobs, use `actions/setup-python` with `cache: 'pip'`.
- [ ] In R jobs, use `r-lib/actions/setup-r-dependencies` to cache installed packages across runs.
- [ ] Re-run the workflow and compare runtime improvement after cache warm-up.

---

# 📤 To Submit

- For credit: one screenshot of a successful **Model Training** GitHub Actions run with the `xgboost-model` artifact.

---

![](../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
