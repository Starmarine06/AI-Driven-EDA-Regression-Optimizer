from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from ci_simulator import (
    SimulatorContext,
    compare_baseline_vs_optimized,
    load_context,
    prioritize_tests_for_commit,
)
from config import DEFAULT_DOLLAR_PER_COMPUTE_HOUR


@st.cache_resource
def get_context() -> SimulatorContext:
    return load_context()


def main() -> None:
    st.set_page_config(page_title="AI-Driven EDA Regression Optimizer", layout="wide")

    ctx = get_context()
    commits = ctx.data.commits
    modules = ctx.data.modules
    tests = ctx.data.tests

    st.title("AI-Driven EDA Regression Optimizer")
    st.markdown(
        """
This dashboard demonstrates a **predictive RTL verification engine** that
reorders regression tests based on **failure risk**, rather than running
all tests blindly.
        """
    )

    # Sidebar controls
    st.sidebar.header("Controls")
    recent_commits = commits.sort_values("timestamp").tail(500)
    default_commit_id = recent_commits["commit_id"].iloc[-1]

    commit_id = st.sidebar.selectbox(
        "Select commit",
        options=recent_commits["commit_id"],
        index=len(recent_commits) - 1,
    )

    dollar_per_hour = st.sidebar.slider(
        "Compute cost ($ per hour)",
        min_value=0.5,
        max_value=10.0,
        value=float(DEFAULT_DOLLAR_PER_COMPUTE_HOUR),
        step=0.5,
    )

    st.sidebar.caption("Commit IDs are synthetic; each has a realistic mix of modules and tests.")

    # Core computations
    prioritized = prioritize_tests_for_commit(commit_id, ctx)
    metrics = compare_baseline_vs_optimized(commit_id, ctx)

    # Risk overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Selected Commit",
            commit_id,
        )
    with col2:
        avg_risk = float(prioritized["predicted_fail_prob"].mean())
        st.metric("Avg Predicted Failure Prob", f"{avg_risk:.2%}")
    with col3:
        high_risk_count = int((prioritized["predicted_fail_prob"] > prioritized["predicted_fail_prob"].quantile(0.8)).sum())
        st.metric("High-Risk Tests (Top 20%)", high_risk_count)
    with col4:
        baseline_runtime_hours = metrics["baseline_total_runtime_sec"] / 3600.0
        est_cost = baseline_runtime_hours * dollar_per_hour
        st.metric("Baseline Full Regression Cost", f"${est_cost:,.2f}")

    st.markdown("### Test Prioritization Table")
    show_cols = [
        "priority_rank",
        "test_id",
        "primary_module",
        "category",
        "typical_runtime_seconds",
        "predicted_fail_prob",
    ]
    table_df = prioritized[show_cols].copy()
    table_df["predicted_fail_prob"] = (table_df["predicted_fail_prob"] * 100).round(2)
    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
    )

    # Module heatmap / risk view
    st.markdown("### Module Risk Heatmap (for selected commit)")
    # Approximate per-module risk as max predicted risk among tests touching that module
    module_risk = (
        prioritized.groupby("primary_module")["predicted_fail_prob"]
        .max()
        .reset_index()
        .rename(columns={"primary_module": "module_id", "predicted_fail_prob": "risk"})
    )
    mod_with_meta = module_risk.merge(modules, on="module_id", how="left")

    if not mod_with_meta.empty:
        fig = px.treemap(
            mod_with_meta,
            path=["logical_block", "module_id"],
            values="lines_of_code",
            color="risk",
            color_continuous_scale="Reds",
            title="Module Heatmap (size=LOC, color=risk)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No module risk data available for this commit.")

    # ROI panel
    st.markdown("### ROI: Time-to-First-Failure and Compute Savings")
    roi_cols = st.columns(3)
    with roi_cols[0]:
        if metrics["baseline_time_to_first_failure_sec"] is not None:
            st.metric(
                "Baseline Time-to-First-Failure",
                f"{metrics['baseline_time_to_first_failure_sec']:.1f} s",
            )
        else:
            st.metric("Baseline Time-to-First-Failure", "No failures")

    with roi_cols[1]:
        if metrics["optimized_time_to_first_failure_sec"] is not None:
            st.metric(
                "Optimized Time-to-First-Failure",
                f"{metrics['optimized_time_to_first_failure_sec']:.1f} s",
            )
        else:
            st.metric("Optimized Time-to-First-Failure", "No failures")

    with roi_cols[2]:
        if metrics["saved_seconds"] is not None:
            saved_hours = metrics["saved_seconds"] / 3600.0
            dollar_savings = saved_hours * dollar_per_hour
            st.metric(
                "Estimated Savings per Run",
                f"${dollar_savings:,.2f}",
                help="Based on reduction in time-to-first-failure and the selected $/hour.",
            )
        else:
            st.metric("Estimated Savings per Run", "$0.00")

    st.markdown(
        """
#### How to Interpret This
- **High-risk tests** bubble to the top of the list, so verification engineers
  get failure signals *earlier*.
- The **module heatmap** highlights which parts of the chip are currently
  most at risk for the selected commit.
- The **ROI panel** translates schedule improvements into approximate
  compute cost savings.
        """
    )


if __name__ == "__main__":
    main()

