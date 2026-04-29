# fastapi/main.py
# FastAPI REST Endpoint (Brussels Realtime)
# Pairs with 03_serve_model.R
# Tim Fraser

# 0. SETUP ###################################

from fastapi import FastAPI
import xgboost as xgb
import numpy as np
from pathlib import Path
import json


def resolve_model_path() -> Path:
    candidates = [
        Path("data/modelpy.json"),
        Path("../data/modelpy.json"),
        Path("12_end/data/modelpy.json"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def resolve_validation_path() -> Path:
    candidates = [
        Path("data/validationpy.json"),
        Path("../data/validationpy.json"),
        Path("12_end/data/validationpy.json"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]

# 1. LOAD MODEL ###################################

app = FastAPI()
model = xgb.Booster()
model.load_model(str(resolve_model_path()))
validation_path = resolve_validation_path()
validation = json.loads(validation_path.read_text(encoding="utf-8"))
default_standard_error = float(validation.get("residual_standard_error_default", validation.get("test_rmse", 0.0)))
se_by_hour_day = {
    (int(row["day_of_week"]), int(row["hour_of_day"])): float(row["standard_error"])
    for row in validation.get("standard_error_by_hour_day", [])
}

# 2. DEFINE ENDPOINT ###################################

@app.get("/predict")
def predict(day_of_week: int, hour_of_day: int):
    features = np.array([[day_of_week, hour_of_day]], dtype=float)
    dmat = xgb.DMatrix(features, feature_names=["day_of_week", "hour_of_day"])
    pred = model.predict(dmat)
    standard_error = se_by_hour_day.get((int(day_of_week), int(hour_of_day)), default_standard_error)
    return {
        "predicted_vehicle_count": round(float(pred[0]), 1),
        "standard_error": round(float(standard_error), 3),
        "standard_error_method": validation.get("standard_error_method"),
    }


@app.get("/validation")
def get_validation():
    return {
        "metro_id": validation.get("metro_id"),
        "test_rmse": validation.get("test_rmse"),
        "test_r_squared": validation.get("test_r_squared"),
        "train_rmse": validation.get("train_rmse"),
        "train_r_squared": validation.get("train_r_squared"),
    }
