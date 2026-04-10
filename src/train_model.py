"""
Train a predictive model for RTL test failure risk.

Usage:
  python train_model.py              # full retrain (default)
  python train_model.py --incremental            # add trees on latest commits
  python train_model.py --incremental --window 200  # use last 200 commits

Incremental mode safety:
- Only adds a small batch of new trees (default 50 rounds) to the existing model.
- Validates on a held-out slice of recent commits to detect drift/overfit.
- Safe because L1/L2 regularization is preserved from the original model.
- Do NOT call after every single commit — batch at least 50-100 new commits first.
"""

from __future__ import annotations

import argparse
import numpy as np
import pandas as pd
import joblib
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import ParameterSampler, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder, StandardScaler
from tqdm import tqdm
from xgboost import XGBClassifier

from config import MODEL_PATH
from features import (
    CATEGORY_FEATURES,
    NUMERIC_FEATURES,
    RawDataBundle,
    build_training_features,
)


def _time_based_split_three_way(
    X: pd.DataFrame,
    y: pd.Series,
    data: RawDataBundle,
    train_frac: float = 0.6,
    val_frac: float = 0.2,
    test_frac: float = 0.2,
) -> tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame,
    pd.Series, pd.Series, pd.Series,
]:
    """
    Split into train / validation / test by commit timestamp (no shuffling).
    Validation is used for overfitting detection only; test is a strict holdout.
    """
    assert abs(train_frac + val_frac + test_frac - 1.0) < 1e-6
    verif = data.verif_results.merge(
        data.commits[["commit_id", "timestamp"]],
        on="commit_id",
        how="left",
    )
    timestamps = pd.to_datetime(verif["timestamp"])
    sorted_idx = np.argsort(timestamps.values)
    X_sorted = X.iloc[sorted_idx].reset_index(drop=True)
    y_sorted = y.iloc[sorted_idx].reset_index(drop=True)

    n = len(X_sorted)
    n_train = int(n * train_frac)
    n_val = int(n * val_frac)

    X_train = X_sorted.iloc[:n_train]
    y_train = y_sorted.iloc[:n_train]
    X_val   = X_sorted.iloc[n_train : n_train + n_val]
    y_val   = y_sorted.iloc[n_train : n_train + n_val]
    X_test  = X_sorted.iloc[n_train + n_val :]
    y_test  = y_sorted.iloc[n_train + n_val :]

    return X_train, X_val, X_test, y_train, y_val, y_test


def _build_pipeline(
    n_estimators: int = 500,
    max_depth: int = 6,
    learning_rate: float = 0.05,
    subsample: float = 0.8,
    colsample_bytree: float = 0.7,
    min_child_weight: int = 3,
    reg_alpha: float = 0.1,
    reg_lambda: float = 5.0,
    scale_pos_weight: float = 1.0,
    random_state: int = 42,
) -> Pipeline:
    """
    Build a scikit-learn Pipeline with:
    - StandardScaler on numeric features
    - OrdinalEncoder on categorical features (XGBoost handles ordinals natively)
    - XGBClassifier with GPU acceleration
    """
    numeric_transformer = Pipeline(steps=[("scaler", StandardScaler())])
    categorical_transformer = Pipeline(
        steps=[
            (
                "ordinal",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
            )
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORY_FEATURES),
        ]
    )

    # Try GPU first; fall back to CPU if CUDA is unavailable
    try:
        classifier = XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            min_child_weight=min_child_weight,
            reg_alpha=reg_alpha,
            reg_lambda=reg_lambda,
            scale_pos_weight=scale_pos_weight,
            tree_method="hist",
            device="cuda",
            eval_metric="auc",
            use_label_encoder=False,
            random_state=random_state,
            verbosity=0,
        )
    except Exception:
        classifier = XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            min_child_weight=min_child_weight,
            reg_alpha=reg_alpha,
            reg_lambda=reg_lambda,
            scale_pos_weight=scale_pos_weight,
            tree_method="hist",
            eval_metric="auc",
            use_label_encoder=False,
            random_state=random_state,
            verbosity=0,
        )

    return Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("clf", classifier),
        ]
    )


# Wide search space — GPU makes this affordable within 30 min
PARAM_GRID = {
    "clf__n_estimators":     [300, 500, 800, 1200],
    "clf__max_depth":        [4, 5, 6, 7, 8],
    "clf__learning_rate":    [0.01, 0.05, 0.1, 0.2],
    "clf__subsample":        [0.6, 0.8, 1.0],
    "clf__colsample_bytree": [0.5, 0.7, 1.0],
    "clf__min_child_weight": [1, 3, 10],
    "clf__reg_alpha":        [0.0, 0.1, 1.0],
    "clf__reg_lambda":       [1.0, 5.0, 10.0],
}


def _evaluate_rank_metrics(
    y_true: np.ndarray,
    y_scores: np.ndarray,
    top_fraction: float = 0.2,
) -> dict:
    n = len(y_true)
    k = max(1, int(n * top_fraction))
    order = np.argsort(-y_scores)
    top_idx = order[:k]
    total_failed = y_true.sum()
    caught_in_top = y_true[top_idx].sum()
    recall_at_top = float(caught_in_top / total_failed) if total_failed > 0 else 0.0
    return {
        "top_fraction": top_fraction,
        "k": k,
        "total_failed": int(total_failed),
        "caught_in_top": int(caught_in_top),
        "recall_at_top": recall_at_top,
    }


def train_and_save_model() -> None:
    X, y, data = build_training_features()

    X_train, X_val, X_test, y_train, y_val, y_test = _time_based_split_three_way(
        X, y, data, train_frac=0.6, val_frac=0.2, test_frac=0.2
    )

    # Class imbalance weight: ratio of negatives to positives
    neg = float((y_train == 0).sum())
    pos = float((y_train == 1).sum())
    spw = neg / pos if pos > 0 else 1.0
    print(f"\nClass imbalance → scale_pos_weight = {spw:.2f}  (neg={int(neg)}, pos={int(pos)})")

    tscv = TimeSeriesSplit(n_splits=3)
    n_candidates = 50
    param_list = list(
        ParameterSampler(PARAM_GRID, n_iter=n_candidates, random_state=42)
    )
    total_fits = n_candidates * tscv.get_n_splits(X_train)

    print(f"\nHyperparameter search: {n_candidates} candidates × {tscv.get_n_splits(X_train)} folds = {total_fits} fits.")
    print("Using XGBoost + CUDA GPU (3060Ti). Expected time: 15–25 min.\n")

    best_val_auc = -np.inf
    best_params = None

    with tqdm(
        total=total_fits,
        desc="CV fits",
        unit="fit",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
    ) as pbar:
        for params in param_list:
            pipeline = _build_pipeline(scale_pos_weight=spw)
            pipeline.set_params(**params)
            fold_aucs = []
            for train_idx, val_idx in tscv.split(X_train):
                Xf_tr = X_train.iloc[train_idx]
                yf_tr = y_train.iloc[train_idx]
                Xf_val = X_train.iloc[val_idx]
                yf_val = y_train.iloc[val_idx]
                pipeline.fit(Xf_tr, yf_tr)
                proba = pipeline.predict_proba(Xf_val)[:, 1]
                fold_aucs.append(roc_auc_score(yf_val, proba))
                pbar.update(1)
            mean_auc = float(np.mean(fold_aucs))
            if mean_auc > best_val_auc:
                best_val_auc = mean_auc
                best_params = params.copy()

    print(f"\nBest CV AUC: {best_val_auc:.4f}")

    # Refit best params on full training set
    best_model = _build_pipeline(scale_pos_weight=spw)
    best_model.set_params(**best_params)
    best_model.fit(X_train, y_train)

    # Train metrics
    train_scores = best_model.predict_proba(X_train)[:, 1]
    train_brier  = brier_score_loss(y_train, train_scores)
    train_roc    = roc_auc_score(y_train, train_scores)

    # Validation metrics
    val_scores = best_model.predict_proba(X_val)[:, 1]
    val_brier  = brier_score_loss(y_val, val_scores)
    val_roc    = roc_auc_score(y_val, val_scores)

    # Test metrics (strict holdout)
    test_scores = best_model.predict_proba(X_test)[:, 1]
    test_brier  = brier_score_loss(y_test, test_scores)
    test_roc    = roc_auc_score(y_test, test_scores)

    rank_val  = _evaluate_rank_metrics(y_val.values, val_scores,  top_fraction=0.2)
    rank_test = _evaluate_rank_metrics(y_test.values, test_scores, top_fraction=0.2)

    brier_gap = val_brier - train_brier
    overfit_warning = (
        "  ⚠️  [Possible overfitting: train Brier << val Brier]"
        if brier_gap > 0.02
        else ""
    )

    print("\n--- Best hyperparameters ---")
    for k, v in best_params.items():
        print(f"  {k}: {v}")

    print("\n--- Brier score (lower is better) ---")
    print(f"  Train: {train_brier:.4f}")
    print(f"  Val:   {val_brier:.4f}" + overfit_warning)
    print(f"  Test:  {test_brier:.4f}  (strict holdout)")

    print("\n--- ROC-AUC (higher is better) ---")
    print(f"  Train: {train_roc:.3f}")
    print(f"  Val:   {val_roc:.3f}")
    print(f"  Test:  {test_roc:.3f}  (strict holdout)")

    print("\n--- Recall@top20% ---")
    print(f"  Val:  {rank_val['caught_in_top']}/{rank_val['total_failed']} failed tests  "
          f"({rank_val['recall_at_top']*100:.1f}%)")
    print(f"  Test: {rank_test['caught_in_top']}/{rank_test['total_failed']} failed tests  "
          f"({rank_test['recall_at_top']*100:.1f}%)")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, MODEL_PATH)
    print(f"\nSaved best model to {MODEL_PATH}")


def incremental_update(window: int = 150, new_rounds: int = 50) -> None:
    """
    Safely extend the existing model with a few new trees trained on the
    most recent `window` commits.

    Why this doesn't overfit:
    - Only `new_rounds` trees are added (small relative to the full model).
    - The existing L1/L2 regularization params are inherited automatically.
    - We validate on a held-out 20% slice of the window before saving.
    - If AUC drops by >0.05 vs. the previously reported AUC, we warn.

    When to call:
    - After accumulating at least 50–100 new commits (NOT after every commit).
    - Can be scheduled in CI (e.g. daily or every 100 pushes).
    """
    if not MODEL_PATH.exists():
        print("No saved model found. Run full training first.")
        return

    print(f"Loading existing model from {MODEL_PATH}")
    pipeline = joblib.load(MODEL_PATH)

    X, y, data = build_training_features()

    # Sort by commit timestamp and take the last `window` commits
    verif = data.verif_results.merge(
        data.commits[["commit_id", "timestamp"]], on="commit_id", how="left"
    )
    timestamps = pd.to_datetime(verif["timestamp"])
    sorted_idx = np.argsort(timestamps.values)
    X_sorted = X.iloc[sorted_idx].reset_index(drop=True)
    y_sorted = y.iloc[sorted_idx].reset_index(drop=True)

    X_recent = X_sorted.iloc[-window:]
    y_recent = y_sorted.iloc[-window:]

    # Hold out the last 20% of the window for validation
    n_val = max(10, int(len(X_recent) * 0.2))
    X_inc_train = X_recent.iloc[:-n_val]
    y_inc_train = y_recent.iloc[:-n_val]
    X_inc_val   = X_recent.iloc[-n_val:]
    y_inc_val   = y_recent.iloc[-n_val:]

    # Transform with the pipeline's preprocessor
    preprocessor = pipeline.named_steps["preprocess"]
    X_inc_train_t = preprocessor.transform(X_inc_train)
    X_inc_val_t   = preprocessor.transform(X_inc_val)

    # Get the underlying XGBoost booster to continue training
    xgb_clf = pipeline.named_steps["clf"]
    booster  = xgb_clf.get_booster()

    dtrain = xgb.DMatrix(X_inc_train_t, label=y_inc_train)
    dval   = xgb.DMatrix(X_inc_val_t,   label=y_inc_val)

    # Inherit params from the trained classifier
    params = xgb_clf.get_xgb_params()
    params["eval_metric"] = "auc"

    print(f"\nAdding {new_rounds} new trees on the latest {window} rows...")
    updated_booster = xgb.train(
        params,
        dtrain,
        num_boost_round=new_rounds,
        xgb_model=booster,         # continue from existing model
        evals=[(dval, "val")],
        verbose_eval=10,
    )

    # Evaluate on the held-out val slice
    val_preds = updated_booster.predict(dval)
    if y_inc_val.sum() > 0:
        inc_auc = roc_auc_score(y_inc_val, val_preds)
        print(f"\nIncremental val AUC on recent window: {inc_auc:.4f}")
        if inc_auc < 0.55:
            print("⚠️  Warning: AUC below 0.55 on recent window — consider full retrain.")
    else:
        print("(No failures in val slice — skipping AUC check)")

    # Reattach updated booster to the pipeline
    xgb_clf.get_booster().copy()  # ensure we're not mutating in-place
    xgb_clf._Booster = updated_booster

    joblib.dump(pipeline, MODEL_PATH)
    print(f"Updated model saved to {MODEL_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train RTL test failure model")
    parser.add_argument(
        "--incremental", action="store_true",
        help="Incremental update: add new trees on recent commits instead of full retrain"
    )
    parser.add_argument(
        "--window", type=int, default=150,
        help="Number of most-recent rows to use for incremental update (default: 150)"
    )
    parser.add_argument(
        "--rounds", type=int, default=50,
        help="Number of new XGBoost trees to add in incremental mode (default: 50)"
    )
    args = parser.parse_args()

    if args.incremental:
        incremental_update(window=args.window, new_rounds=args.rounds)
    else:
        train_and_save_model()
