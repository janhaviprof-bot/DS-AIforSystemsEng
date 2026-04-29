# 02_train_model.py
# Train XGBoost Model (Brussels Realtime)
# Pairs with 02_train_model.R
# Tim Fraser

# 0. SETUP ###################################

## 0.1 Load Packages #################################

import numpy as np
import pandas as pd
import sqlite3
import xgboost as xgb
import json
from pathlib import Path

# 1. CONFIG ###################################

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DB_PATH = SCRIPT_DIR / "data" / "traffic.db"
MODEL_PATH = DATA_DIR / "modelpy.json"
VALIDATION_PATH = DATA_DIR / "validationpy.json"
METRO_ID = 948

DATA_DIR.mkdir(parents=True, exist_ok=True)

# 2. LOAD DATA ###################################

conn = sqlite3.connect(str(DB_PATH))
df = pd.read_sql(
    "SELECT observed_at, vehicles FROM traffic WHERE metro_id = ? ORDER BY observed_at",
    conn,
    params=(METRO_ID,),
)
conn.close()

# 3. FEATURE ENGINEERING ###################################

if df.empty:
    raise SystemExit("No rows found for configured METRO_ID.")

df["observed_at"] = pd.to_datetime(df["observed_at"], utc=True)
df["day_of_week"] = df["observed_at"].dt.dayofweek + 1
df["hour_of_day"] = df["observed_at"].dt.hour

features = ["day_of_week", "hour_of_day"]

# 4. TRAIN/TEST SPLIT ###################################

df = df.reset_index(drop=True)
df["row_id"] = np.arange(1, len(df) + 1)

train_df = df.sample(frac=0.8)
test_df = df[~df["row_id"].isin(train_df["row_id"])].copy()

train_df = train_df.drop(columns=["row_id"])
test_df = test_df.drop(columns=["row_id"])

if train_df.empty or test_df.empty:
    raise SystemExit("Need at least 2 rows so both train and test sets are non-empty.")

X_train = train_df[features].to_numpy()
y_train = train_df["vehicles"].to_numpy()
X_test = test_df[features].to_numpy()
y_test = test_df["vehicles"].to_numpy()

# 5. TRAIN MODEL ###################################

dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=features)

params = {
    "objective": "reg:squarederror",
    "max_depth": 4,
    "eta": 0.1,
    "verbosity": 0,
}

model = xgb.train(params, dtrain, num_boost_round=50)

# 6. EVALUATE ###################################

pred_train = model.predict(dtrain)
train_rmse = np.sqrt(np.mean((pred_train - y_train) ** 2))
train_r_squared = 1 - np.sum((y_train - pred_train) ** 2) / np.sum((y_train - np.mean(y_train)) ** 2)

dtest = xgb.DMatrix(X_test, label=y_test, feature_names=features)
pred_test = model.predict(dtest)
test_rmse = np.sqrt(np.mean((pred_test - y_test) ** 2))
test_r_squared = 1 - np.sum((y_test - pred_test) ** 2) / np.sum((y_test - np.mean(y_test)) ** 2)

test_eval = test_df[["day_of_week", "hour_of_day"]].copy()
test_eval["residual"] = y_test - pred_test
uncertainty_df = (
    test_eval.groupby(["day_of_week", "hour_of_day"], as_index=False)
    .agg(standard_error=("residual", "std"), n=("residual", "size"))
)
uncertainty_df["standard_error"] = uncertainty_df["standard_error"].fillna(float(test_rmse))
uncertainty_rows = [
    {
        "day_of_week": int(row.day_of_week),
        "hour_of_day": int(row.hour_of_day),
        "standard_error": float(row.standard_error),
        "n": int(row.n),
    }
    for row in uncertainty_df.itertuples(index=False)
]

print(f"Training RMSE: {train_rmse:.2f}")
print(f"Training R-squared: {train_r_squared:.3f}")
print(f"Testing RMSE: {test_rmse:.2f}")
print(f"Testing R-squared: {test_r_squared:.3f}")

# 7. SAVE MODEL ###################################

model.save_model(str(MODEL_PATH))

validation = {
    "metro_id": int(METRO_ID),
    "test_rmse": float(test_rmse),
    "test_r_squared": float(test_r_squared),
    "train_rmse": float(train_rmse),
    "train_r_squared": float(train_r_squared),
    "residual_standard_error_default": float(test_rmse),
    "standard_error_method": "Residual SD on held-out test split by day_of_week/hour_of_day; fallback to test RMSE.",
    "standard_error_by_hour_day": uncertainty_rows,
}
VALIDATION_PATH.write_text(json.dumps(validation, indent=2), encoding="utf-8")

print("\n====================================================")
print("02_train_model.py | Brussels realtime model")
print("====================================================")
print(f"   metro_id: {METRO_ID}")
print(f"   train rows (80%): {len(train_df)}")
print(f"   test rows (20%): {len(test_df)}")
print("   features: day_of_week, hour_of_day")
print(f"   model saved to {MODEL_PATH}")
print(f"   validation saved to {VALIDATION_PATH}")
