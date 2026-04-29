# 📌 ACTIVITY

## Train Model with Weekly Cron Job

🕒 *Estimated Time: 10-15 minutes*

---

## ✅ Your Task

Train an XGBoost model using Brussels rows for one `metro_id`, then run weekly retraining in GitHub Actions.

### 🧱 Stage 1: Train locally

- [ ] Open [`02_train_model.R`](02_train_model.R) or [`02_train_model.py`](02_train_model.py).
- [ ] Confirm `METRO_ID` is set to Brussels (default `948`).
- [ ] Run the script from `12_end/`.
- [ ] Confirm `data/modelr.json` (R) or `data/modelpy.json` (Python) is created and RMSE is printed.

```
Model saved to data/modelr.json
Training RMSE: 142.35
```

### 🧱 Stage 2: Automate weekly retraining

- [ ] Open [`.github/workflows/12-train-r.yml`](../.github/workflows/12-train-r.yml) or [`.github/workflows/12-train-python.yml`](../.github/workflows/12-train-python.yml) and inspect the weekly cron schedule.
- [ ] Confirm `train_r`/`train_python` job runs.
- [ ] Trigger the workflow manually from **Actions**.
- [ ] Confirm workflows commits its own files: R writes `data/modelr.json` and Python writes `data/modelpy.json`.


---

# 📤 To Submit

- For credit: one screenshot of a successful **Model Training** GitHub Actions run with the `xgboost-model` artifact.

---

![](../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
