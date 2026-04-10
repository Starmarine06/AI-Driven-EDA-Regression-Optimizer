"""
CI/CD optimizer simulation.

Uses the trained model to:
- Score all tests for a given commit.
- Produce a prioritized regression order.
- Compare baseline vs optimized time-to-first-failure using historical outcomes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

import joblib
import numpy as np
import pandas as pd

from config import DEFAULT_DOLLAR_PER_COMPUTE_HOUR, MODEL_PATH
from features import RawDataBundle, build_candidate_features_for_commit, load_raw_data


@dataclass
class SimulatorContext:
    data: RawDataBundle
    model: object  # sklearn Pipeline


def load_context() -> SimulatorContext:
    data = load_raw_data()
    model = joblib.load(MODEL_PATH)
    return SimulatorContext(data=data, model=model)


def prioritize_tests_for_commit(
    commit_id: str,
    ctx: SimulatorContext,
) -> pd.DataFrame:
    """
    Return a dataframe with one row per test for the given commit,
    including predicted failure probability and ranking.
    """
    commits = ctx.data.commits
    tests = ctx.data.tests
    modules = ctx.data.modules

    commit_row = commits.loc[commits["commit_id"] == commit_id]
    if commit_row.empty:
        raise ValueError(f"Unknown commit_id: {commit_id}")
    commit_row = commit_row.iloc[0]

    X_candidates = build_candidate_features_for_commit(commit_row, tests, modules)
    scores = ctx.model.predict_proba(X_candidates)[:, 1]

    result = tests.copy()
    result["predicted_fail_prob"] = scores

    # Higher risk first
    result = result.sort_values("predicted_fail_prob", ascending=False).reset_index(drop=True)
    result["priority_rank"] = np.arange(1, len(result) + 1)
    return result


def compute_time_to_first_failure(
    commit_id: str,
    ordering: pd.Series,
    ctx: SimulatorContext,
) -> Optional[float]:
    """
    Compute realized time-to-first-failure for a given commit and test ordering,
    using the historical verif_results.
    Returns total simulation time in seconds, or None if no failures occurred.
    """
    verif = ctx.data.verif_results
    tests = ctx.data.tests.set_index("test_id")

    subset = verif[verif["commit_id"] == commit_id]
    if subset.empty:
        return None

    failed_tests = set(subset.loc[subset["passed"] == 0, "test_id"].unique())
    if not failed_tests:
        return None

    total_time = 0.0
    for test_id in ordering:
        runtime = float(tests.loc[test_id, "typical_runtime_seconds"])
        total_time += runtime
        if test_id in failed_tests:
            return total_time

    return None


def compare_baseline_vs_optimized(commit_id: str, ctx: SimulatorContext) -> dict:
    """
    Compare baseline (runtime-ordered) vs optimized (ML risk-ordered) schedules.
    """
    tests = ctx.data.tests

    prioritized = prioritize_tests_for_commit(commit_id, ctx)

    baseline_order = tests.sort_values("typical_runtime_seconds")["test_id"]
    optimized_order = prioritized["test_id"]

    ttf_baseline = compute_time_to_first_failure(commit_id, baseline_order, ctx)
    ttf_optimized = compute_time_to_first_failure(commit_id, optimized_order, ctx)

    baseline_total_runtime = float(tests["typical_runtime_seconds"].sum())

    result = {
        "commit_id": commit_id,
        "baseline_time_to_first_failure_sec": ttf_baseline,
        "optimized_time_to_first_failure_sec": ttf_optimized,
        "baseline_total_runtime_sec": baseline_total_runtime,
    }

    if ttf_baseline is not None and ttf_optimized is not None:
        saved_seconds = max(0.0, ttf_baseline - ttf_optimized)
        result["saved_seconds"] = saved_seconds
        result["saved_fraction_vs_baseline"] = (
            saved_seconds / ttf_baseline if ttf_baseline > 0 else 0.0
        )

        hours = saved_seconds / 3600.0
        result["estimated_dollar_savings"] = hours * DEFAULT_DOLLAR_PER_COMPUTE_HOUR
    else:
        result["saved_seconds"] = None
        result["saved_fraction_vs_baseline"] = None
        result["estimated_dollar_savings"] = None

    return result


def demo_once() -> None:
    """
    Run a single demo comparing baseline vs optimized ordering for
    a random recent commit.
    """
    ctx = load_context()
    commits = ctx.data.commits

    # Focus on more recent commits to show realistic behavior
    recent_commits = commits.sort_values("timestamp").tail(500)
    commit_id = random.choice(recent_commits["commit_id"].tolist())

    print(f"Evaluating commit: {commit_id}")
    metrics = compare_baseline_vs_optimized(commit_id, ctx)

    print("Baseline vs Optimized time-to-first-failure (seconds):")
    print(
        f"  Baseline:  {metrics['baseline_time_to_first_failure_sec']:.2f}"
        if metrics["baseline_time_to_first_failure_sec"] is not None
        else "  Baseline:  no failing tests observed"
    )
    print(
        f"  Optimized: {metrics['optimized_time_to_first_failure_sec']:.2f}"
        if metrics["optimized_time_to_first_failure_sec"] is not None
        else "  Optimized: no failing tests observed"
    )

    if metrics["saved_seconds"] is not None:
        print(
            f"  Saved {metrics['saved_seconds']:.2f}s "
            f"({metrics['saved_fraction_vs_baseline']:.1%}) "
            f"~ ${metrics['estimated_dollar_savings']:.2f} per run"
        )


if __name__ == "__main__":
    demo_once()

