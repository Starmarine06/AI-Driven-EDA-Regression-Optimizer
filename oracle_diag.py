"""Diagnose oracle AUC ceiling and data pipeline correctness."""
import pandas as pd
import numpy as np
import sys

sys.path.insert(0, "src")
from features import load_raw_data
from config import (
    BASE_FAILURE_RATE,
    HIGH_RISK_MODULE_MULTIPLIER,
    JUNIOR_AUTHOR_MULTIPLIER,
    RUNTIME_FAILURE_MULTIPLIER,
)
from sklearn.metrics import roc_auc_score

data = load_raw_data()

print("=== Commits CSV columns ===")
print(data.commits.columns.tolist())

# Join everything (same as training)
verif = data.verif_results.copy()
verif = verif.merge(data.commits, on="commit_id", how="left")
verif = verif.merge(data.tests, on="test_id", how="left")
verif = verif.merge(data.modules, on="module_id", how="left")
verif["failed"] = 1 - verif["passed"]

print("\n=== Author experience score ===")
print("Is in commits.csv:", "author_experience_score" in data.commits.columns)
print("Is in joined table:", "author_experience_score" in verif.columns)

mr = data.modules.set_index("module_id")["historical_bug_count"]
mr_max = float(mr.max())

def touched_risk_fn(s):
    parts = [m.strip() for m in str(s).split(",") if m.strip()]
    if parts:
        return float(mr.reindex(parts).fillna(0).mean())
    return 0.0

touched_risk = verif["modules_touched"].apply(touched_risk_fn).values
primary_risk = mr.reindex(verif["module_id"]).fillna(0).values
risk = (touched_risk / (mr_max + 1e-6) + primary_risk / (mr_max + 1e-6)) / 2.0
mod_f = 1.0 + risk * (HIGH_RISK_MODULE_MULTIPLIER - 1.0)

# Use actual DGP author experience (from joined table)
auth_exp = verif["author_experience_score"].fillna(0.5).values
auth_f = 1.0 + (1.0 - auth_exp) * (JUNIOR_AUTHOR_MULTIPLIER - 1.0)

comp_f = 1.0 + verif["complexity_score"].fillna(0.5).values * (RUNTIME_FAILURE_MULTIPLIER - 1.0)
frag_f = 1.0 + (1.0 - verif["historical_pass_rate"].values) * 2.0

oracle = np.clip(BASE_FAILURE_RATE * mod_f * auth_f * comp_f * frag_f, 0.01, 0.9)
y = verif["failed"].values

print("\n=== Oracle AUC (best possible given DGP signals) ===")
print("Oracle AUC (all 4 signals):", round(roc_auc_score(y, oracle), 4))
print("AUC (no author):           ", round(roc_auc_score(y, np.clip(BASE_FAILURE_RATE * mod_f * comp_f * frag_f, 0.01, 0.9)), 4))
print("AUC (mod+frag only):       ", round(roc_auc_score(y, np.clip(BASE_FAILURE_RATE * mod_f * frag_f, 0.01, 0.9)), 4))

print("\n=== p_fail distribution ===")
print(f"  min={oracle.min():.4f}  max={oracle.max():.4f}  mean={oracle.mean():.4f}  std={oracle.std():.4f}")
print(f"  max/min ratio: {oracle.max()/oracle.min():.1f}x")

print("\n=== Feature correlations with failure ===")
for feat in ["complexity_score", "historical_bug_count", "historical_pass_rate",
             "commit_touches_test_module", "author_experience_score", "module_bug_density"]:
    if feat in verif.columns:
        corr = np.corrcoef(y, verif[feat].fillna(0).values)[0, 1]
        print(f"  {feat}: {corr:.4f}")
    else:
        verif["module_bug_density"] = verif["historical_bug_count"] / (verif["lines_of_code"] + 1e-6)
        corr = np.corrcoef(y, verif["module_bug_density"].fillna(0).values)[0, 1]
        print(f"  module_bug_density (derived): {corr:.4f}")
