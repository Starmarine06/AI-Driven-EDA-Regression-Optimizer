"""
prediction_server.py — FastAPI server that loads the XGBoost model and predicts.
Runs on port 8000. The React frontend calls POST /predict.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib
import numpy as np
from datetime import datetime
import os

# ── Exact model paths ──────────────────────────────────────────────────────────
MODELS_DIR  = r"C:\Users\flame\Documents\SandiskAI\rtl_verification_system\models"
MODEL_PATH  = os.path.join(MODELS_DIR, "rtl_predictor_model.pkl")
SCALER_PATH = os.path.join(MODELS_DIR, "scaler.pkl")
FEAT_PATH   = os.path.join(MODELS_DIR, "feature_cols.pkl")

# ── Load model at startup ──────────────────────────────────────────────────────
print(f"Loading model from {MODEL_PATH} ...")
model        = joblib.load(MODEL_PATH)
scaler       = joblib.load(SCALER_PATH)
feature_cols = joblib.load(FEAT_PATH)
print(f"✓ Model loaded: {type(model).__name__}, {len(feature_cols)} features")
print(f"✓ Features: {feature_cols}")

app = FastAPI(title="RTL Failure Predictor")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Request schema (5 user inputs) ─────────────────────────────────────────────
class PredictRequest(BaseModel):
    code_churn_ratio: float = 0.5
    files_modified: int = 10
    author_experience_years: int = 5
    historical_bug_frequency: float = 0.3
    modules_affected_count: int = 3

# ── /predict endpoint ──────────────────────────────────────────────────────────
@app.post("/predict")
def predict(req: PredictRequest):
    # Derive all 13 features (mirrors train_model.py)
    is_hotspot_module     = 0
    has_critical_module   = 0
    lines_added           = int(req.code_churn_ratio * req.files_modified * 15)
    lines_deleted         = int(req.code_churn_ratio * req.files_modified * 8)
    regression_time_hours = max(0.5, req.files_modified * 0.3)
    code_churn_normalized = req.code_churn_ratio * req.files_modified
    bug_density           = req.historical_bug_frequency / (req.modules_affected_count + 1)
    risk_score_raw        = (
        (1 - req.author_experience_years / 20) * 0.2 +
        req.code_churn_ratio * 0.3 +
        is_hotspot_module * 0.2 +
        (bug_density / (bug_density if bug_density > 0 else 1e-9)) * 0.3
    )

    feature_vector = {
        "author_experience_years":  req.author_experience_years,
        "files_modified":           req.files_modified,
        "lines_added":              lines_added,
        "lines_deleted":            lines_deleted,
        "modules_affected_count":   req.modules_affected_count,
        "code_churn_ratio":         req.code_churn_ratio,
        "is_hotspot_module":        is_hotspot_module,
        "historical_bug_frequency": req.historical_bug_frequency,
        "regression_time_hours":    regression_time_hours,
        "has_critical_module":      has_critical_module,
        "code_churn_normalized":    code_churn_normalized,
        "bug_density":              round(bug_density, 6),
        "risk_score":               round(risk_score_raw, 6),
    }

    # Predict
    X        = np.array([[feature_vector[col] for col in feature_cols]])
    X_scaled = scaler.transform(X)
    prob     = float(model.predict_proba(X_scaled)[0][1])
    risk     = round(prob * 100, 1)
    level    = "HIGH" if risk > 70 else "MEDIUM" if risk > 40 else "LOW"

    model_ts = datetime.fromtimestamp(os.path.getmtime(MODEL_PATH)).strftime("%Y-%m-%d %H:%M")

    # Console log
    print(f"[predict] churn={req.code_churn_ratio} files={req.files_modified} exp={req.author_experience_years} "
          f"bugs={req.historical_bug_frequency} mods={req.modules_affected_count} → risk={risk} ({level})")

    return {
        "risk_score":          risk,
        "failure_probability": round(prob, 4),
        "risk_level":          level,
        "prediction_source":   "xgboost_model",
        "model_timestamp":     model_ts,
        "feature_vector":      feature_vector,
        "recommendation": {
            "HIGH":   "High failure risk. Run full regression suite and request a senior RTL review before merge.",
            "MEDIUM": "Moderate risk. Run targeted regression on affected modules and verify timing constraints.",
            "LOW":    "Low risk change. Standard smoke-test regression is sufficient before merge.",
        }[level],
    }

# ── /model-status endpoint ─────────────────────────────────────────────────────
@app.get("/model-status")
def model_status():
    # Run a quick sanity check
    low_vec  = [15, 2, 12, 5, 1, 0.1, 0, 0.05, 0.6, 0, 0.2, 0.025, 0.1]
    high_vec = [0, 40, 480, 240, 12, 0.9, 1, 0.9, 12.0, 1, 36.0, 0.069, 0.95]

    low_prob  = float(model.predict_proba(scaler.transform(np.array([low_vec])))[0][1])
    high_prob = float(model.predict_proba(scaler.transform(np.array([high_vec])))[0][1])

    return {
        "status":       "OK",
        "model_path":   MODEL_PATH,
        "model_type":   type(model).__name__,
        "feature_cols": feature_cols,
        "model_trained": datetime.fromtimestamp(os.path.getmtime(MODEL_PATH)).strftime("%Y-%m-%d %H:%M:%S"),
        "test_predictions": {
            "low_risk":  {"prob": round(low_prob, 4),  "score": round(low_prob * 100, 1)},
            "high_risk": {"prob": round(high_prob, 4), "score": round(high_prob * 100, 1)},
        },
        "sanity_check": "PASS" if high_prob > low_prob else "FAIL",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
