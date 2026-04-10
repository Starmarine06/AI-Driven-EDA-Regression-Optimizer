"""
test_model.py — Directly test the trained XGBoost model
Loads model from exact path, takes user inputs, prints risk score + failure probability.
"""

import joblib
import numpy as np

# ── Exact model paths ──────────────────────────────────────────────────────────
MODEL_PATH  = r"C:\Users\flame\Documents\SandiskAI\rtl_verification_system\models\rtl_predictor_model.pkl"
SCALER_PATH = r"C:\Users\flame\Documents\SandiskAI\rtl_verification_system\models\scaler.pkl"
FEAT_PATH   = r"C:\Users\flame\Documents\SandiskAI\rtl_verification_system\models\feature_cols.pkl"

def main():
    # Load model
    print("\n" + "=" * 60)
    print("  LOADING XGBOOST MODEL")
    print("=" * 60)
    print(f"  Model : {MODEL_PATH}")
    print(f"  Scaler: {SCALER_PATH}")
    print(f"  Feats : {FEAT_PATH}")

    model       = joblib.load(MODEL_PATH)
    scaler      = joblib.load(SCALER_PATH)
    feature_cols = joblib.load(FEAT_PATH)

    print(f"\n  ✓ Model loaded successfully!")
    print(f"  ✓ Feature columns ({len(feature_cols)}): {feature_cols}")
    print(f"  ✓ Model type: {type(model).__name__}")

    # Get user inputs
    print("\n" + "=" * 60)
    print("  ENTER FEATURE VALUES")
    print("=" * 60)

    code_churn_ratio         = float(input("  Code Churn Ratio (0.0-1.0)     [0.5]: ") or 0.5)
    files_modified           = int(input("  Files Modified (1-100)          [10]: ") or 10)
    author_experience_years  = int(input("  Author Experience Years (0-20)   [5]: ") or 5)
    historical_bug_frequency = float(input("  Historical Bug Frequency (0-1) [0.3]: ") or 0.3)
    modules_affected_count   = int(input("  Modules Affected Count (1-15)    [3]: ") or 3)

    # Derive remaining features (mirrors train_model.py exactly)
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

    # Build feature vector in exact column order
    feature_vector = {
        'author_experience_years':  author_experience_years,
        'files_modified':           files_modified,
        'lines_added':              lines_added,
        'lines_deleted':            lines_deleted,
        'modules_affected_count':   modules_affected_count,
        'code_churn_ratio':         code_churn_ratio,
        'is_hotspot_module':        is_hotspot_module,
        'historical_bug_frequency': historical_bug_frequency,
        'regression_time_hours':    regression_time_hours,
        'has_critical_module':      has_critical_module,
        'code_churn_normalized':    code_churn_normalized,
        'bug_density':              bug_density,
        'risk_score':               risk_score_raw,
    }

    print("\n" + "=" * 60)
    print("  FEATURE VECTOR SENT TO MODEL")
    print("=" * 60)
    for col in feature_cols:
        print(f"  {col:<28} = {feature_vector[col]}")

    # Run prediction
    X        = np.array([[feature_vector[col] for col in feature_cols]])
    X_scaled = scaler.transform(X)
    prob     = float(model.predict_proba(X_scaled)[0][1])
    risk     = round(prob * 100, 2)
    level    = "HIGH" if risk > 70 else "MEDIUM" if risk > 40 else "LOW"

    # Color codes
    RED = "\033[91m"; YELLOW = "\033[93m"; GREEN = "\033[92m"; BOLD = "\033[1m"; RESET = "\033[0m"
    color = RED if level == "HIGH" else YELLOW if level == "MEDIUM" else GREEN

    print("\n" + "=" * 60)
    print(f"  {BOLD}PREDICTION RESULT{RESET}")
    print("=" * 60)
    print(f"  Risk Score          : {color}{BOLD}{risk}{RESET}")
    print(f"  Failure Probability : {color}{BOLD}{round(prob, 4)}{RESET}")
    print(f"  Risk Level          : {color}{BOLD}{level}{RESET}")
    print("=" * 60)
    print(f"  Model used: {type(model).__name__} from {MODEL_PATH}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
