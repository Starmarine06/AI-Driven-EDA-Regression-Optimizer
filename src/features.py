"""
Shared feature engineering utilities for training and inference.

This module:
- Loads raw CSVs.
- Joins commits, modules, tests, and verification results.
- Builds a per-(commit, test_id) feature matrix suitable for model training
  and for scoring new commits.

Time-safe rolling features are computed strictly before each commit's
timestamp to prevent data leakage from future results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from config import COMMITS_CSV, MODULES_CSV, TESTS_CSV, VERIF_RESULTS_CSV


NUMERIC_FEATURES = [
    # Commit-level
    "files_changed",
    "lines_added",
    "lines_deleted",
    "total_lines_changed",
    "code_churn_window",
    "complexity_score",
    "author_experience_score",
    "commit_touches_test_module",
    # Module-level static
    "historical_bug_count",
    "avg_bug_severity",
    "avg_fix_time_days",
    "lines_of_code",
    "module_bug_density",
    # Test-level static
    "typical_runtime_seconds",
    "historical_pass_rate",
    # --- Time-aware rolling features (no leakage) ---
    "test_rolling_fail_rate_30d",
    "test_rolling_fail_rate_90d",
    "module_rolling_fail_rate_30d",
    "test_fail_streak",
    "days_since_last_test_run",
    # --- Interaction features (mirror DGP multiplicative structure) ---
    "author_junior_flag",         # 1 if junior (exp < 0.5), amplifies failure prob
    "complexity_x_bug_risk",      # complexity_score * normalized bug count
    "junior_x_bug_risk",          # author_junior_flag * normalized bug count
    "fragility_score",            # 1 - historical_pass_rate  (direct DGP signal)
    "touches_x_bug_risk",         # commit_touches × historical_bug_count (hotspot)
]

CATEGORY_FEATURES = [
    "branch",
    "commit_message_category",
    "logical_block",
    "category",  # test category
]


@dataclass
class RawDataBundle:
    commits: pd.DataFrame
    modules: pd.DataFrame
    tests: pd.DataFrame
    verif_results: pd.DataFrame


def load_raw_data() -> RawDataBundle:
    commits = pd.read_csv(COMMITS_CSV, parse_dates=["timestamp"])
    modules = pd.read_csv(MODULES_CSV)
    tests = pd.read_csv(TESTS_CSV)
    verif_results = pd.read_csv(VERIF_RESULTS_CSV)
    return RawDataBundle(
        commits=commits,
        modules=modules,
        tests=tests,
        verif_results=verif_results,
    )


def _compute_rolling_features(data: RawDataBundle) -> pd.DataFrame:
    """
    Fully vectorized computation of time-aware rolling failure rates and streaks
    per (test_id, commit_id).

    All aggregations use only rows whose timestamp is STRICTLY BEFORE the
    current commit's timestamp — no leakage from the future.

    Strategy:
    - Sort the full history by timestamp once.
    - Use pandas groupby + transform with `expanding()` + time-based windows
      via merge_asof to compute cumulative and windowed statistics.
    - A single merge_asof per feature joins "latest available stat" onto each
      (commit, test/module) pair without ever seeing the future.

    Runtime: ~5-30 seconds for 5000 commits × 150 tests (vs. ~60 min loop).
    """
    # ── Flat history table: one row per (commit, test) execution ────────────
    hist = data.verif_results.merge(
        data.commits[["commit_id", "timestamp"]],
        on="commit_id", how="left",
    )
    hist["failed"] = (1 - hist["passed"]).astype(float)
    hist["timestamp"] = pd.to_datetime(hist["timestamp"])
    hist = hist.sort_values("timestamp").reset_index(drop=True)

    # Commit timestamps for join target
    commit_ts = (
        data.commits[["commit_id", "timestamp"]]
        .drop_duplicates("commit_id")
        .copy()
    )
    commit_ts["timestamp"] = pd.to_datetime(commit_ts["timestamp"])
    commit_ts = commit_ts.sort_values("timestamp").reset_index(drop=True)

    # Pairs we need features for: every (commit_id, test_id) in verif_results
    pairs = data.verif_results[["commit_id", "test_id", "module_id"]].copy()
    pairs = pairs.merge(commit_ts, on="commit_id", how="left")
    pairs = pairs.sort_values("timestamp").reset_index(drop=True)

    # ── Helper: rolling window stat per group using merge_asof ───────────────
    # For each group key (test_id or module_id) we build a time-indexed series
    # of cumulative / window stats, then join via merge_asof (left < right).

    def _rolling_fail_rates_for_group(group_key: str):
        """
        Returns a DataFrame with columns:
          [group_key, 'timestamp', 'rate_30d', 'rate_90d']
        for every unique event in hist, computed up to but NOT including that ts.
        """
        results = []
        for gid, grp in hist.groupby(group_key):
            grp = grp.sort_values("timestamp").reset_index(drop=True)
            # We'll compute stats at each unique timestamp in this group
            # using a sorted expanding window
            ts_vals   = grp["timestamp"].values
            fail_vals = grp["failed"].values
            n = len(grp)

            ts_list = []
            r30_list = []
            r90_list = []

            for i in range(n):
                t = ts_vals[i]
                t30 = t - np.timedelta64(30, "D")
                t90 = t - np.timedelta64(90, "D")
                # Only rows STRICTLY BEFORE index i (i.e. past rows)
                past_ts   = ts_vals[:i]
                past_fail = fail_vals[:i]
                w30 = past_fail[past_ts >= t30]
                w90 = past_fail[past_ts >= t90]
                r30 = float(w30.mean()) if len(w30) > 0 else np.nan
                r90 = float(w90.mean()) if len(w90) > 0 else np.nan
                ts_list.append(t)
                r30_list.append(r30)
                r90_list.append(r90)

            tmp = pd.DataFrame({
                group_key:  gid,
                "timestamp": ts_list,
                "rate_30d":  r30_list,
                "rate_90d":  r90_list,
            })
            results.append(tmp)

        return pd.concat(results, ignore_index=True).sort_values([group_key, "timestamp"])

    def _streak_and_staleness_for_tests():
        """
        Returns a DataFrame with columns:
          ['test_id', 'timestamp', 'test_fail_streak', 'days_since_last_test_run']
        at each event point in hist (before that point).
        """
        results = []
        for tid, grp in hist.groupby("test_id"):
            grp = grp.sort_values("timestamp").reset_index(drop=True)
            ts_vals   = grp["timestamp"].values
            fail_vals = grp["failed"].values
            n = len(grp)

            ts_list     = []
            streak_list = []
            stale_list  = []

            for i in range(n):
                t = ts_vals[i]
                past_ts   = ts_vals[:i]
                past_fail = fail_vals[:i]

                # Consecutive fail streak from the most-recent run backwards
                streak = 0
                for f in past_fail[::-1]:
                    if f == 1:
                        streak += 1
                    else:
                        break

                # Days since last run
                if i > 0:
                    last_ts = past_ts[-1]
                    days_since = (t - last_ts) / np.timedelta64(1, "D")
                else:
                    days_since = 999.0

                ts_list.append(t)
                streak_list.append(streak)
                stale_list.append(days_since)

            tmp = pd.DataFrame({
                "test_id":                  tid,
                "timestamp":                ts_list,
                "test_fail_streak":         streak_list,
                "days_since_last_test_run": stale_list,
            })
            results.append(tmp)

        return pd.concat(results, ignore_index=True).sort_values(["test_id", "timestamp"])

    print("  → Computing per-test rolling failure rates...")
    test_rates = _rolling_fail_rates_for_group("test_id")
    test_rates = test_rates.rename(
        columns={"rate_30d": "test_rolling_fail_rate_30d",
                 "rate_90d": "test_rolling_fail_rate_90d"}
    )

    print("  → Computing per-module rolling failure rates...")
    mod_rates = _rolling_fail_rates_for_group("module_id")
    mod_rates = mod_rates[["module_id", "timestamp", "rate_30d"]].rename(
        columns={"rate_30d": "module_rolling_fail_rate_30d"}
    )

    print("  → Computing test fail streaks and staleness...")
    streaks = _streak_and_staleness_for_tests()

    # ── Join via merge_asof (nearest past row, strictly before commit ts) ─────
    # pairs is sorted by timestamp; each stat table is sorted by (key, timestamp)

    # 1. Test rolling rates
    pairs = pairs.sort_values("timestamp")
    test_rates_sorted = test_rates.sort_values(["test_id", "timestamp"])

    merged = []
    for tid, pgrp in pairs.groupby("test_id"):
        trate = test_rates_sorted[test_rates_sorted["test_id"] == tid].sort_values("timestamp")
        joined = pd.merge_asof(
            pgrp.sort_values("timestamp"),
            trate[["timestamp", "test_rolling_fail_rate_30d", "test_rolling_fail_rate_90d"]],
            on="timestamp",
            direction="backward",
            allow_exact_matches=False,  # strictly BEFORE
        )
        merged.append(joined)
    pairs = pd.concat(merged, ignore_index=True)

    # 2. Module rolling rates
    mod_rates_sorted = mod_rates.sort_values(["module_id", "timestamp"])
    merged2 = []
    for mid, pgrp in pairs.groupby("module_id"):
        mrate = mod_rates_sorted[mod_rates_sorted["module_id"] == mid].sort_values("timestamp")
        joined = pd.merge_asof(
            pgrp.sort_values("timestamp"),
            mrate[["timestamp", "module_rolling_fail_rate_30d"]],
            on="timestamp",
            direction="backward",
            allow_exact_matches=False,
        )
        merged2.append(joined)
    pairs = pd.concat(merged2, ignore_index=True)

    # 3. Streaks + staleness
    streaks_sorted = streaks.sort_values(["test_id", "timestamp"])
    merged3 = []
    for tid, pgrp in pairs.groupby("test_id"):
        sgrp = streaks_sorted[streaks_sorted["test_id"] == tid].sort_values("timestamp")
        joined = pd.merge_asof(
            pgrp.sort_values("timestamp"),
            sgrp[["timestamp", "test_fail_streak", "days_since_last_test_run"]],
            on="timestamp",
            direction="backward",
            allow_exact_matches=False,
        )
        merged3.append(joined)
    pairs = pd.concat(merged3, ignore_index=True)

    # ── Impute NaNs (only early rows with no prior history) ──────────────────
    for col in [
        "test_rolling_fail_rate_30d",
        "test_rolling_fail_rate_90d",
        "module_rolling_fail_rate_30d",
    ]:
        mean_val = pairs[col].mean()
        pairs[col] = pairs[col].fillna(mean_val if pd.notna(mean_val) else 0.05)

    pairs["test_fail_streak"] = pairs["test_fail_streak"].fillna(0)
    pairs["days_since_last_test_run"] = pairs["days_since_last_test_run"].fillna(999.0)

    rolling_df = pairs[
        [
            "commit_id",
            "test_id",
            "test_rolling_fail_rate_30d",
            "test_rolling_fail_rate_90d",
            "module_rolling_fail_rate_30d",
            "test_fail_streak",
            "days_since_last_test_run",
        ]
    ].drop_duplicates(subset=["commit_id", "test_id"])

    return rolling_df


def _join_base_training_table(data: RawDataBundle) -> pd.DataFrame:
    """
    Join commits, tests, modules, and verification outcomes into a base table.
    Each row is a historical (commit, test) execution with outcome.
    """
    df = data.verif_results.merge(
        data.commits,
        on="commit_id",
        how="left",
        suffixes=("", "_commit"),
    )

    df = df.merge(
        data.tests,
        left_on="test_id",
        right_on="test_id",
        how="left",
        suffixes=("", "_test"),
    )

    df = df.merge(
        data.modules,
        left_on="module_id",
        right_on="module_id",
        how="left",
        suffixes=("", "_module"),
    )

    # Derived features
    df["module_bug_density"] = df["historical_bug_count"] / (df["lines_of_code"] + 1e-6)

    # Strong signal: did this commit touch the module under test?
    mods_touched_sets = df["modules_touched"].apply(
        lambda s: set(m.strip() for m in str(s).split(",") if m.strip())
    )
    df["commit_touches_test_module"] = [
        1 if mid in touched else 0
        for mid, touched in zip(df["module_id"], mods_touched_sets)
    ]

    # --- Interaction features (mirror DGP multiplicative structure) ----------
    # Normalise bug count to [0,1] for interactions
    bc_max = df["historical_bug_count"].max() + 1e-6
    bc_norm = df["historical_bug_count"] / bc_max

    df["author_junior_flag"] = (df["author_experience_score"].fillna(0.5) < 0.5).astype(float)
    df["complexity_x_bug_risk"] = df["complexity_score"].fillna(0.5) * bc_norm
    df["junior_x_bug_risk"]     = df["author_junior_flag"] * bc_norm
    df["fragility_score"]       = 1.0 - df["historical_pass_rate"].fillna(0.9)
    df["touches_x_bug_risk"]    = df["commit_touches_test_module"] * df["historical_bug_count"]

    return df


def make_feature_matrix(
    df: pd.DataFrame,
    include_target: bool = True,
) -> Tuple[pd.DataFrame, Optional[pd.Series]]:
    """
    Given a base table (either from history or synthetic candidates),
    compute the feature columns and (optionally) the target label.
    """
    if "module_bug_density" not in df.columns:
        df = df.copy()
        df["module_bug_density"] = df["historical_bug_count"] / (df["lines_of_code"] + 1e-6)

    # Fill rolling + interaction features if missing (inference path)
    bc_max = df["historical_bug_count"].max() + 1e-6 if "historical_bug_count" in df.columns else 1.0
    for col, default in [
        ("test_rolling_fail_rate_30d",   0.05),
        ("test_rolling_fail_rate_90d",   0.05),
        ("module_rolling_fail_rate_30d", 0.05),
        ("test_fail_streak",             0.0),
        ("days_since_last_test_run",     999.0),
        ("author_junior_flag",           0.0),
        ("complexity_x_bug_risk",        0.0),
        ("junior_x_bug_risk",            0.0),
        ("fragility_score",              0.05),
        ("touches_x_bug_risk",           0.0),
    ]:
        if col not in df.columns:
            df = df.copy()
            df[col] = default

    # Recompute interaction features if base columns available but interactions missing
    if "author_junior_flag" not in df.columns or df["author_junior_flag"].isna().all():
        df = df.copy()
        bc_norm = df.get("historical_bug_count", 0) / bc_max
        df["author_junior_flag"]    = (df["author_experience_score"].fillna(0.5) < 0.5).astype(float)
        df["complexity_x_bug_risk"] = df["complexity_score"].fillna(0.5) * bc_norm
        df["junior_x_bug_risk"]     = df["author_junior_flag"] * bc_norm
        df["fragility_score"]       = 1.0 - df["historical_pass_rate"].fillna(0.9)
        df["touches_x_bug_risk"]    = df["commit_touches_test_module"] * df.get("historical_bug_count", 0)

    y = None
    if include_target and "passed" in df.columns:
        y = (1 - df["passed"]).astype(int)

    X = df[NUMERIC_FEATURES + CATEGORY_FEATURES].copy()
    return X, y


def build_training_features() -> Tuple[pd.DataFrame, pd.Series, RawDataBundle]:
    """
    High-level helper for training:
    - Load raw CSVs
    - Compute time-safe rolling features
    - Build base training table
    - Produce feature matrix X, target y, and return raw data bundle
    """
    data = load_raw_data()

    print("Computing time-aware rolling features (no leakage)...")
    rolling_df = _compute_rolling_features(data)

    base_df = _join_base_training_table(data)

    # Merge rolling features in
    base_df = base_df.merge(rolling_df, on=["commit_id", "test_id"], how="left")

    X, y = make_feature_matrix(base_df, include_target=True)
    assert y is not None, "Target vector y could not be constructed."
    return X, y, data


def build_candidate_features_for_commit(
    commit_row: pd.Series,
    tests: pd.DataFrame,
    modules: pd.DataFrame,
    rolling_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Build a candidate feature matrix for *all* tests for a given commit.
    This is used at inference time when scoring a new or existing commit.
    rolling_df: optional pre-computed rolling features to join in.
    """
    base = pd.DataFrame(
        {
            "commit_id": commit_row["commit_id"],
            "test_id": tests["test_id"].values,
            "module_id": tests["primary_module"].values,
        }
    )

    for col in [
        "files_changed",
        "lines_added",
        "lines_deleted",
        "total_lines_changed",
        "code_churn_window",
        "complexity_score",
        "author_experience_score",
        "branch",
        "commit_message_category",
    ]:
        if col in commit_row.index:
            base[col] = commit_row[col]
        elif col == "author_experience_score":
            base[col] = 0.5

    mods_touched = [m.strip() for m in str(commit_row.get("modules_touched", "") or "").split(",") if m.strip()]
    base["commit_touches_test_module"] = base["module_id"].isin(mods_touched).astype(int)

    base = base.join(
        tests[
            [
                "test_id",
                "primary_module",
                "category",
                "typical_runtime_seconds",
                "historical_pass_rate",
            ]
        ].set_index("test_id"),
        on="test_id",
    )

    base = base.merge(
        modules[
            [
                "module_id",
                "logical_block",
                "historical_bug_count",
                "avg_bug_severity",
                "avg_fix_time_days",
                "lines_of_code",
            ]
        ],
        left_on="module_id",
        right_on="module_id",
        how="left",
    )

    # Attach rolling features if provided
    if rolling_df is not None:
        base = base.merge(rolling_df, on=["commit_id", "test_id"], how="left")

    X, _ = make_feature_matrix(base, include_target=False)
    return X
