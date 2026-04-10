"""
AI-Enabled Debug Prioritization from Simulation Logs
=====================================================

Analyses simulation failure data to:
1. Identify unique failure signatures (de-duplicate and cluster similar failures)
2. Categorize failures by type: UVM, SVA, Functional, Performance, Security
3. Prioritize errors for faster debug closure using an impact × severity × novelty score
4. Highlight recent commits most likely to have introduced each failure cluster
5. Produce: prioritized failure list, categorized error summary, suggested debug starting points
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from config import COMMITS_CSV, MODULES_CSV, TESTS_CSV, VERIF_RESULTS_CSV

# ---------------------------------------------------------------------------
# Failure category mapping
# ---------------------------------------------------------------------------
# Maps (test_category, logical_block) → realistic simulation failure type
CATEGORY_MAP: Dict[tuple, str] = {
    # SMOKE failures → critical path / bus interface (UVM sequence errors)
    ("SMOKE", "CPU"):       "UVM_SEQUENCE",
    ("SMOKE", "GPU"):       "UVM_SEQUENCE",
    ("SMOKE", "DSP"):       "UVM_SEQUENCE",
    ("SMOKE", "FABRIC"):    "UVM_CONNECTIVITY",
    ("SMOKE", "MEM_CTRL"): "UVM_CONNECTIVITY",
    ("SMOKE", "IO"):        "UVM_CONNECTIVITY",
    ("SMOKE", "SECURITY"):  "SECURITY_POLICY",
    ("SMOKE", "POWER_MGMT"): "POWER_SEQUENCE",
    # CORNER failures → boundary / assertion checks
    ("CORNER", "CPU"):      "SVA_ASSERTION",
    ("CORNER", "GPU"):      "SVA_ASSERTION",
    ("CORNER", "DSP"):      "SVA_ASSERTION",
    ("CORNER", "FABRIC"):   "SVA_PROTOCOL",
    ("CORNER", "MEM_CTRL"): "SVA_PROTOCOL",
    ("CORNER", "IO"):       "SVA_PROTOCOL",
    ("CORNER", "SECURITY"): "SECURITY_POLICY",
    ("CORNER", "POWER_MGMT"): "POWER_SEQUENCE",
    # REGRESSION failures → functional correctness
    ("REGRESSION", "CPU"):       "FUNCTIONAL",
    ("REGRESSION", "GPU"):       "FUNCTIONAL",
    ("REGRESSION", "DSP"):       "FUNCTIONAL",
    ("REGRESSION", "FABRIC"):    "FUNCTIONAL",
    ("REGRESSION", "MEM_CTRL"):  "FUNCTIONAL",
    ("REGRESSION", "IO"):        "FUNCTIONAL",
    ("REGRESSION", "SECURITY"):  "SECURITY_POLICY",
    ("REGRESSION", "POWER_MGMT"): "POWER_SEQUENCE",
}

CATEGORY_SEVERITY: Dict[str, int] = {
    "SECURITY_POLICY":   5,
    "SVA_ASSERTION":     4,
    "SVA_PROTOCOL":      4,
    "UVM_SEQUENCE":      3,
    "UVM_CONNECTIVITY":  3,
    "FUNCTIONAL":        3,
    "POWER_SEQUENCE":    2,
}


@dataclass
class FailureCluster:
    """A group of similar failures sharing module + category."""
    cluster_id: str
    failure_type: str
    module_id: str
    logical_block: str
    test_ids: List[str]
    commit_ids: List[str]
    total_failures: int
    unique_tests_affected: int
    severity: int
    first_seen: str   # ISO timestamp
    last_seen: str
    likely_culprit_commits: List[str]
    debug_hint: str
    priority_score: float = 0.0


@dataclass
class DebugReport:
    clusters: List[FailureCluster]
    categorized_summary: pd.DataFrame
    prioritized_list: pd.DataFrame
    suggested_starting_points: List[str]


# ---------------------------------------------------------------------------
# Core loading and analysis
# ---------------------------------------------------------------------------

def _load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    verif   = pd.read_csv(VERIF_RESULTS_CSV)
    commits = pd.read_csv(COMMITS_CSV, parse_dates=["timestamp"])
    tests   = pd.read_csv(TESTS_CSV)
    modules = pd.read_csv(MODULES_CSV)
    return verif, commits, tests, modules


def _classify_failure(test_category: str, logical_block: str) -> str:
    key = (test_category, logical_block)
    return CATEGORY_MAP.get(key, "FUNCTIONAL")


def _build_failure_table(
    verif: pd.DataFrame,
    commits: pd.DataFrame,
    tests: pd.DataFrame,
    modules: pd.DataFrame,
    lookback_commits: Optional[int] = None,
) -> pd.DataFrame:
    """
    Join all tables and filter to failures only.
    If lookback_commits is set, only return failures from the most recent N commits.
    """
    failures = verif[verif["passed"] == 0].copy()

    failures = failures.merge(
        commits[["commit_id", "timestamp", "author_id", "author_experience_score",
                 "complexity_score", "modules_touched", "branch", "commit_message_category"]],
        on="commit_id", how="left",
    )
    failures = failures.merge(
        tests[["test_id", "category", "typical_runtime_seconds", "historical_pass_rate"]],
        on="test_id", how="left",
    )
    failures = failures.merge(
        modules[["module_id", "logical_block", "historical_bug_count",
                 "avg_bug_severity", "avg_fix_time_days"]],
        on="module_id", how="left",
    )

    failures["failure_type"] = failures.apply(
        lambda r: _classify_failure(r["category"], r["logical_block"]), axis=1
    )
    failures["severity"] = failures["failure_type"].map(CATEGORY_SEVERITY).fillna(3).astype(int)
    failures["timestamp"] = pd.to_datetime(failures["timestamp"])

    if lookback_commits is not None:
        recent_commits = (
            failures[["commit_id", "timestamp"]]
            .drop_duplicates("commit_id")
            .nlargest(lookback_commits, "timestamp")["commit_id"]
        )
        failures = failures[failures["commit_id"].isin(recent_commits)]

    return failures


def cluster_failures(failures: pd.DataFrame) -> List[FailureCluster]:
    """
    Cluster failures by (module_id, failure_type) — each cluster represents
    a distinct failure signature that needs a debug ticket.
    """
    clusters: List[FailureCluster] = []
    grouped = failures.groupby(["module_id", "failure_type"])

    all_commits_ts = failures[["commit_id", "timestamp"]].drop_duplicates("commit_id")

    for (mod_id, ftype), grp in grouped:
        grp_sorted = grp.sort_values("timestamp")

        logical_block = grp["logical_block"].iloc[0]
        severity = int(grp["severity"].iloc[0])
        test_ids = grp["test_id"].unique().tolist()
        commit_ids = grp["commit_id"].unique().tolist()
        first_seen = str(grp_sorted["timestamp"].iloc[0])[:19]
        last_seen  = str(grp_sorted["timestamp"].iloc[-1])[:19]

        # --- Likely culprit commits ---
        # Commits where: (a) they touched this module, (b) had high complexity,
        # (c) failures appear shortly after
        touched = grp_sorted[
            grp_sorted["modules_touched"].str.contains(mod_id, na=False)
        ]["commit_id"].unique()[:3].tolist()
        if not touched:
            # Fall back to highest-complexity commits in this cluster
            touched = (
                grp_sorted.nlargest(min(3, len(grp_sorted)), "complexity_score")["commit_id"]
                .unique().tolist()
            )

        # --- Debug hint ---
        avg_fix = grp["avg_fix_time_days"].mean()
        dominant_branch = grp["branch"].mode()[0] if not grp["branch"].isna().all() else "unknown"
        hint = _generate_debug_hint(ftype, logical_block, dominant_branch, avg_fix)

        # --- Priority score = unique_tests × severity × novelty ---
        # novelty: how recently this cluster appeared (more recent = higher priority)
        freshness = (grp["timestamp"].max() - failures["timestamp"].min()).total_seconds()
        total_range = (failures["timestamp"].max() - failures["timestamp"].min()).total_seconds() + 1
        novelty = freshness / total_range

        priority = len(test_ids) * severity * (1 + novelty)

        clusters.append(FailureCluster(
            cluster_id=f"{mod_id}::{ftype}",
            failure_type=ftype,
            module_id=mod_id,
            logical_block=logical_block,
            test_ids=test_ids,
            commit_ids=commit_ids,
            total_failures=len(grp),
            unique_tests_affected=len(test_ids),
            severity=severity,
            first_seen=first_seen,
            last_seen=last_seen,
            likely_culprit_commits=touched[:3],
            debug_hint=hint,
            priority_score=round(priority, 2),
        ))

    clusters.sort(key=lambda c: c.priority_score, reverse=True)
    return clusters


def _generate_debug_hint(
    ftype: str, block: str, branch: str, avg_fix_days: float
) -> str:
    hints = {
        "UVM_SEQUENCE":    f"Check UVM sequences targeting {block}. Likely a drive/response mismatch on {branch}. Avg fix: {avg_fix_days:.1f}d.",
        "UVM_CONNECTIVITY": f"Connectivity/TLM port issue in {block}. Verify interface bindings added in recent commits on {branch}.",
        "SVA_ASSERTION":   f"SystemVerilog assertion failing in {block}. Look for unintended state changes — check waveforms at assertion trigger.",
        "SVA_PROTOCOL":    f"Protocol-level SVA failing in {block}. Check AXI/AHB handshake signal integrity in recent {branch} changes.",
        "FUNCTIONAL":      f"Functional mismatch in {block}. Compare golden reference vs DUT output. Start with changed RTL files on {branch}.",
        "SECURITY_POLICY": f"SECURITY: access policy violation in {block}. Immediate priority — review permission register changes in recent commits.",
        "POWER_SEQUENCE":  f"Power sequencing error in {block}. Check domain enable/disable order in clock/reset network.",
    }
    return hints.get(ftype, f"Investigate {ftype} failures in {block}.")


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(
    lookback_commits: Optional[int] = 200,
    min_failures: int = 2,
) -> DebugReport:
    """
    Main entry point. Returns a DebugReport with:
    - clusters: ranked FailureCluster objects
    - categorized_summary: DataFrame grouped by failure_type
    - prioritized_list: flat DataFrame sorted by priority
    - suggested_starting_points: top 5 natural-language debug recommendations
    """
    verif, commits, tests, modules = _load_data()
    failures = _build_failure_table(verif, commits, tests, modules, lookback_commits)

    if failures.empty:
        return DebugReport([], pd.DataFrame(), pd.DataFrame(), ["No failures found in lookback window."])

    clusters = cluster_failures(failures)
    # Filter to clusters with enough failures to be meaningful
    clusters = [c for c in clusters if c.total_failures >= min_failures]

    # ── Categorized summary ──────────────────────────────────────────────────
    cat_summary = (
        failures.groupby("failure_type")
        .agg(
            total_failures=("passed", "count"),
            unique_tests_affected=("test_id", "nunique"),
            unique_modules_affected=("module_id", "nunique"),
            avg_severity=("severity", "mean"),
            avg_fix_days=("avg_fix_time_days", "mean"),
        )
        .reset_index()
        .sort_values("total_failures", ascending=False)
        .round(2)
    )

    # ── Prioritized list ─────────────────────────────────────────────────────
    rows = []
    for rank, c in enumerate(clusters, 1):
        rows.append({
            "rank":                   rank,
            "cluster_id":             c.cluster_id,
            "failure_type":           c.failure_type,
            "logical_block":          c.logical_block,
            "module_id":              c.module_id,
            "unique_tests_affected":  c.unique_tests_affected,
            "total_failures":         c.total_failures,
            "severity":               c.severity,
            "first_seen":             c.first_seen,
            "last_seen":              c.last_seen,
            "culprit_commits":        ", ".join(c.likely_culprit_commits[:2]),
            "priority_score":         c.priority_score,
            "debug_hint":             c.debug_hint,
        })
    prio_df = pd.DataFrame(rows)

    # ── Suggested starting points (top 5 human-readable) ────────────────────
    suggestions = []
    for c in clusters[:5]:
        suggestions.append(
            f"[{c.failure_type} | Severity {c.severity}] {c.module_id} — "
            f"{c.unique_tests_affected} tests affected. "
            f"Investigate: {c.likely_culprit_commits[0] if c.likely_culprit_commits else 'unknown commit'}. "
            f"Hint: {c.debug_hint}"
        )

    return DebugReport(
        clusters=clusters,
        categorized_summary=cat_summary,
        prioritized_list=prio_df,
        suggested_starting_points=suggestions,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _print_report(report: DebugReport, top_n: int = 10) -> None:
    print("\n" + "=" * 70)
    print("  AI-ENABLED DEBUG PRIORITIZATION REPORT")
    print("=" * 70)

    print("\n── CATEGORIZED ERROR SUMMARY ──────────────────────────────────────")
    print(report.categorized_summary.to_string(index=False))

    print("\n── TOP PRIORITIZED FAILURES ───────────────────────────────────────")
    top = report.prioritized_list.head(top_n)
    for _, row in top.iterrows():
        print(f"\n  #{int(row['rank'])}  [{row['failure_type']}]  {row['module_id']}  "
              f"(severity={row['severity']}, score={row['priority_score']})")
        print(f"      Tests affected : {row['unique_tests_affected']}  |  "
              f"Total failures: {row['total_failures']}")
        print(f"      Last seen      : {row['last_seen']}")
        print(f"      Culprit commits: {row['culprit_commits']}")
        print(f"      Debug hint     : {row['debug_hint']}")

    print("\n── SUGGESTED STARTING POINTS FOR DEBUG ────────────────────────────")
    for i, sp in enumerate(report.suggested_starting_points, 1):
        print(f"\n  {i}. {sp}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Debug Prioritization from Simulation Logs")
    parser.add_argument("--lookback", type=int, default=200,
                        help="Number of most-recent commits to analyse (default: 200)")
    parser.add_argument("--top", type=int, default=10,
                        help="Number of top failure clusters to show (default: 10)")
    parser.add_argument("--min-failures", type=int, default=2,
                        help="Minimum failures per cluster to include (default: 2)")
    args = parser.parse_args()

    report = generate_report(lookback_commits=args.lookback, min_failures=args.min_failures)
    _print_report(report, top_n=args.top)
