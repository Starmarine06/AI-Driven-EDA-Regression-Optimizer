"""
predict_cli.py  —  Standalone RTL Failure Prediction Client
============================================================
Loads the XGBoost model directly from disk, computes all features,
sends them to the running Flask API, and prints the result to console.

Usage:
    python predict_cli.py
    python predict_cli.py --churn 0.8 --files 30 --exp 2 --bugs 0.6 --mods 8
"""

import argparse
import json
import sys
import requests
import joblib
import numpy as np

# ── Absolute paths (always correct regardless of cwd) ─────────────────────────
MODEL_PATH    = r"C:\Users\flame\Documents\SandiskAI\rtl_verification_system\models\rtl_predictor_model.pkl"
SCALER_PATH   = r"C:\Users\flame\Documents\SandiskAI\rtl_verification_system\models\scaler.pkl"
FEAT_PATH     = r"C:\Users\flame\Documents\SandiskAI\rtl_verification_system\models\feature_cols.pkl"
API_ENDPOINT  = "http://127.0.0.1:5000/api/predictor"

# ── Parse CLI arguments ────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="RTL Failure Risk Predictor")
    p.add_argument("--churn",  type=float, default=0.5,  help="Code churn ratio (0.0–1.0)")
    p.add_argument("--files",  type=int,   default=10,   help="Files modified")
    p.add_argument("--exp",    type=int,   default=5,    help="Author experience (years)")
    p.add_argument("--bugs",   type=float, default=0.3,  help="Historical bug frequency (0.0–1.0)")
    p.add_argument("--mods",   type=int,   default=3,    help="Modules affected count")
    return p.parse_args()

# ── Build full feature vector ──────────────────────────────────────────────────
def build_features(code_churn_ratio, files_modified, author_experience_years,
                   historical_bug_frequency, modules_affected_count):
    is_hotspot_module     = 0
    has_critical_module   = 0
    lines_added           = int(code_churn_ratio * files_modified * 15)
    lines_deleted         = int(code_churn_ratio * files_modified * 8)
    regression_time_hours = max(0.5, files_modified * 0.3)
    code_churn_normalized = code_churn_ratio * files_modified
    bug_density           = historical_bug_frequency / (modules_affected_count + 1)
    risk_score_raw        = (
        (1 - author_experience_years / 20) * 0.2 +
        code_churn_ratio * 0.3 +
        is_hotspot_module * 0.2 +
        (bug_density / (bug_density if bug_density > 0 else 1e-9)) * 0.3
    )

    return {
        "author_experience_years":  author_experience_years,
        "files_modified":           files_modified,
        "lines_added":              lines_added,
        "lines_deleted":            lines_deleted,
        "modules_affected_count":   modules_affected_count,
        "code_churn_ratio":         code_churn_ratio,
        "is_hotspot_module":        is_hotspot_module,
        "historical_bug_frequency": historical_bug_frequency,
        "regression_time_hours":    regression_time_hours,
        "has_critical_module":      has_critical_module,
        "code_churn_normalized":    code_churn_normalized,
        "bug_density":              round(bug_density, 6),
        "risk_score":               round(risk_score_raw, 6),
    }

# ── Direct model prediction (no API needed) ────────────────────────────────────
def predict_direct(features: dict) -> dict:
    print("\n[LOCAL] Loading model from disk...")
    model       = joblib.load(MODEL_PATH)
    scaler      = joblib.load(SCALER_PATH)
    feat_cols   = joblib.load(FEAT_PATH)
    print(f"[LOCAL] Feature order: {feat_cols}")

    X         = np.array([[features[c] for c in feat_cols]])
    X_scaled  = scaler.transform(X)
    prob      = float(model.predict_proba(X_scaled)[0][1])
    risk      = round(prob * 100, 2)
    level     = "HIGH" if risk > 70 else "MEDIUM" if risk > 40 else "LOW"
    return {"risk_score": risk, "failure_probability": round(prob, 4), "risk_level": level, "source": "direct"}

# ── API prediction ─────────────────────────────────────────────────────────────
def predict_via_api(features: dict) -> dict:
    print(f"\n[API]  POST {API_ENDPOINT}")
    print(f"[API]  Payload: {json.dumps(features, indent=2)}")
    resp = requests.post(API_ENDPOINT, json=features, timeout=10)
    resp.raise_for_status()
    return resp.json()

# ── Pretty print result ────────────────────────────────────────────────────────
def print_result(label: str, result: dict):
    lvl = result.get("risk_level", "?")
    color = "\033[91m" if lvl == "HIGH" else "\033[93m" if lvl == "MEDIUM" else "\033[92m"
    reset = "\033[0m"
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Risk Score         : {color}{result.get('risk_score', '?')}{reset}")
    print(f"  Failure Probability: {result.get('failure_probability', '?')}")
    print(f"  Risk Level         : {color}{lvl}{reset}")
    if "recommendation" in result:
        print(f"  Recommendation     : {result['recommendation']}")
    if "model_timestamp" in result:
        print(f"  Model Timestamp    : {result['model_timestamp']}")
    print(f"  Source             : {result.get('prediction_source', result.get('source', '?'))}")
    print(f"{'='*60}\n")

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    args = parse_args()

    print("\n" + "="*60)
    print("  RTL FAILURE RISK PREDICTOR")
    print("="*60)
    print(f"  code_churn_ratio         = {args.churn}")
    print(f"  files_modified           = {args.files}")
    print(f"  author_experience_years  = {args.exp}")
    print(f"  historical_bug_frequency = {args.bugs}")
    print(f"  modules_affected_count   = {args.mods}")

    features = build_features(
        code_churn_ratio         = args.churn,
        files_modified           = args.files,
        author_experience_years  = args.exp,
        historical_bug_frequency = args.bugs,
        modules_affected_count   = args.mods,
    )

    print("\n[INFO] Full feature vector sent to model:")
    for k, v in features.items():
        print(f"       {k:<28} = {v}")

    # 1. Direct model prediction
    try:
        direct = predict_direct(features)
        print_result("DIRECT MODEL RESULT", direct)
    except Exception as e:
        print(f"[WARN] Direct prediction failed: {e}")

    # 2. API prediction
    try:
        api_result = predict_via_api(features)
        print_result("API RESULT (via Flask server)", api_result)
    except requests.exceptions.ConnectionError:
        print("\n[WARN] API server not reachable at", API_ENDPOINT)
        print("       Start it with: python rtl_verification_system/api_server.py")
    except Exception as e:
        print(f"[WARN] API prediction failed: {e}")

if __name__ == "__main__":
    main()
