"""
Synthetic RTL verification history generator.

Generates four CSVs:
- commits.csv: commit-level metadata
- modules.csv: RTL modules with inherent risk characteristics
- tests.csv: verification tests mapped to modules
- verif_results.csv: historical pass/fail outcomes per (commit, test)
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import List

import numpy as np
import pandas as pd

from config import (
    BASE_FAILURE_RATE,
    COMMITS_CSV,
    DATA_DIR,
    HIGH_RISK_MODULE_MULTIPLIER,
    JUNIOR_AUTHOR_MULTIPLIER,
    NUM_AUTHORS,
    NUM_COMMITS,
    NUM_MODULES,
    NUM_TESTS,
    RUNTIME_FAILURE_MULTIPLIER,
    MODULES_CSV,
    TESTS_CSV,
    VERIF_RESULTS_CSV,
)


rng = np.random.default_rng(seed=42)


LOGICAL_BLOCKS = [
    "CPU",
    "GPU",
    "DSP",
    "FABRIC",
    "MEM_CTRL",
    "IO",
    "SECURITY",
    "POWER_MGMT",
]

TEST_CATEGORIES = ["SMOKE", "REGRESSION", "CORNER"]


def generate_modules(num_modules: int) -> pd.DataFrame:
    module_ids = [f"MOD_{i:03d}" for i in range(num_modules)]

    logical_blocks = rng.choice(LOGICAL_BLOCKS, size=num_modules)

    # Heavy-tailed bug count: a few modules are very bug-prone
    raw_bug_counts = rng.pareto(a=2.5, size=num_modules) * 5
    historical_bug_count = np.round(raw_bug_counts).astype(int) + rng.integers(
        0, 3, size=num_modules
    )

    avg_bug_severity = np.clip(
        rng.normal(loc=2.5, scale=0.8, size=num_modules) + (historical_bug_count > 10) * 0.5,
        1.0,
        5.0,
    )

    avg_fix_time = np.clip(
        rng.normal(loc=3.0, scale=1.0, size=num_modules)
        + (historical_bug_count > 10) * 2.0,
        0.5,
        None,
    )

    loc = rng.integers(200, 20000, size=num_modules)

    modules_df = pd.DataFrame(
        {
            "module_id": module_ids,
            "logical_block": logical_blocks,
            "historical_bug_count": historical_bug_count,
            "avg_bug_severity": avg_bug_severity,
            "avg_fix_time_days": avg_fix_time,
            "lines_of_code": loc,
        }
    )

    return modules_df


def generate_authors(num_authors: int) -> pd.DataFrame:
    author_ids = [f"ENG_{i:02d}" for i in range(num_authors)]

    # Randomly mark some as senior, some as junior
    senior_mask = rng.random(size=num_authors) < 0.4
    author_experience_score = np.where(
        senior_mask,
        rng.uniform(0.7, 1.0, size=num_authors),  # seniors
        rng.uniform(0.2, 0.7, size=num_authors),  # juniors
    )

    authors_df = pd.DataFrame(
        {
            "author_id": author_ids,
            "author_experience_score": author_experience_score,
            "is_senior": senior_mask.astype(int),
        }
    )

    return authors_df


def generate_tests(num_tests: int, modules_df: pd.DataFrame) -> pd.DataFrame:
    test_ids = [f"TST_{i:04d}" for i in range(num_tests)]

    primary_modules = rng.choice(modules_df["module_id"], size=num_tests)

    # Some tests touch multiple modules (integration)
    secondary_modules = []
    for _ in range(num_tests):
        if rng.random() < 0.25:
            k = rng.integers(1, 3)
            mods = rng.choice(modules_df["module_id"], size=k, replace=False)
            secondary_modules.append(",".join(mods))
        else:
            secondary_modules.append("")

    categories = rng.choice(TEST_CATEGORIES, size=num_tests, p=[0.2, 0.5, 0.3])

    # Runtime: smoke (short), corner (medium), regression (wide)
    runtimes = []
    for cat in categories:
        if cat == "SMOKE":
            runtimes.append(rng.normal(5, 2))
        elif cat == "CORNER":
            runtimes.append(rng.normal(30, 10))
        else:  # REGRESSION
            runtimes.append(rng.normal(60, 20))
    runtimes = np.clip(runtimes, 1.0, None)

    # Historical pass rate depends on module risk
    module_risk = modules_df.set_index("module_id")["historical_bug_count"]
    risk_vals = module_risk.reindex(primary_modules).values
    # Normalize using np.ptp for compatibility with NumPy 2.x
    scaled_risk = (risk_vals - risk_vals.min()) / (np.ptp(risk_vals) + 1e-6)

    base_pass_rate = 0.95 - scaled_risk * 0.3  # riskier modules fail more
    base_pass_rate = np.clip(base_pass_rate, 0.6, 0.99)

    tests_df = pd.DataFrame(
        {
            "test_id": test_ids,
            "primary_module": primary_modules,
            "secondary_modules": secondary_modules,
            "category": categories,
            "typical_runtime_seconds": runtimes,
            "historical_pass_rate": base_pass_rate,
        }
    )

    return tests_df


def generate_commits(
    num_commits: int,
    modules_df: pd.DataFrame,
    authors_df: pd.DataFrame,
) -> pd.DataFrame:
    commit_ids = [f"CMT_{i:05d}" for i in range(num_commits)]

    start_time = datetime(2024, 1, 1)
    timestamps: List[datetime] = []
    current_time = start_time
    for _ in range(num_commits):
        # between 0 and 8 hours between commits
        delta_hours = rng.uniform(0, 8)
        current_time += timedelta(hours=delta_hours)
        timestamps.append(current_time)

    author_choices = rng.choice(authors_df["author_id"], size=num_commits)

    modules = modules_df["module_id"].tolist()
    module_bug_counts = modules_df.set_index("module_id")["historical_bug_count"]

    files_changed = []
    modules_touched_list = []
    lines_added = []
    lines_deleted = []
    complexity_scores = []
    branches = []
    msg_categories = []

    for _ in range(num_commits):
        num_modules_touched = rng.integers(1, 8)
        touched = rng.choice(modules, size=num_modules_touched, replace=False)
        modules_touched_list.append(",".join(touched))

        # Approximate number of files ~ modules_touched * factor
        files_changed.append(int(num_modules_touched * rng.uniform(1, 3)))

        la = int(rng.normal(200, 150) * (1 + len(touched) / 5))
        ld = int(rng.normal(80, 80) * (1 + len(touched) / 5))
        lines_added.append(max(5, la))
        lines_deleted.append(max(0, ld))

        # Complexity correlated with bug-prone modules
        m_bug_counts = module_bug_counts.reindex(touched).values
        complexity = np.clip(
            rng.normal(0.5, 0.2) + (m_bug_counts.mean() / (module_bug_counts.max() + 1e-6)),
            0.0,
            2.0,
        )
        complexity_scores.append(complexity)

        branches.append(random.choice(["main", "integration", "feature"]))
        msg_categories.append(
            random.choice(["refactor", "feature", "bugfix", "cleanup", "infra"])
        )

    commits_df = pd.DataFrame(
        {
            "commit_id": commit_ids,
            "timestamp": timestamps,
            "author_id": author_choices,
            "files_changed": files_changed,
            "modules_touched": modules_touched_list,
            "lines_added": lines_added,
            "lines_deleted": lines_deleted,
            "complexity_score": complexity_scores,
            "branch": branches,
            "commit_message_category": msg_categories,
        }
    )

    # ── CRITICAL: merge author_experience_score BEFORE returning ─────────────
    # This ensures the same scores used by generate_verification_results()
    # are stored in commits.csv so the model can learn the author signal.
    author_exp_map = authors_df.set_index("author_id")["author_experience_score"]
    commits_df["author_experience_score"] = (
        author_exp_map.reindex(commits_df["author_id"]).values
    )

    # Add a simple rolling code churn metric: last N commits lines changed
    commits_df["total_lines_changed"] = commits_df["lines_added"] + commits_df["lines_deleted"]
    churn_window = 50
    commits_df["code_churn_window"] = (
        commits_df["total_lines_changed"].rolling(churn_window, min_periods=1).sum()
    )

    return commits_df


def generate_verification_results(
    commits_df: pd.DataFrame,
    modules_df: pd.DataFrame,
    tests_df: pd.DataFrame,
    authors_df: pd.DataFrame,
) -> pd.DataFrame:
    module_risk = modules_df.set_index("module_id")["historical_bug_count"]
    # Use the canonical authors_df — same object used during commit generation.
    # (Never call generate_authors_for_lookup which creates new random scores.)
    author_df = authors_df.set_index("author_id")

    rows = []
    for _, commit in commits_df.iterrows():
        # Choose which tests to run for this commit: always smoke + sample of others
        smoke_tests = tests_df[tests_df["category"] == "SMOKE"]
        other_tests = tests_df[tests_df["category"] != "SMOKE"]

        # Sample some regression/corner tests
        num_other = max(5, int(len(other_tests) * 0.2))
        sampled_other = other_tests.sample(
            n=min(num_other, len(other_tests)), random_state=rng.integers(0, 1e9)
        )

        selected_tests = pd.concat([smoke_tests, sampled_other], ignore_index=True)

        # Compute commit-level risk context
        touched_modules = [m for m in commit["modules_touched"].split(",") if m]
        if touched_modules:
            bug_counts = module_risk.reindex(touched_modules).fillna(0).values
            avg_module_bug = bug_counts.mean()
        else:
            avg_module_bug = 0.0

        module_risk_norm = avg_module_bug / (module_risk.max() + 1e-6)

        author_id = commit["author_id"]
        author_row = author_df.loc[author_id]
        author_exp = author_row["author_experience_score"]
        author_is_junior = 1.0 - author_exp  # more junior = closer to 1

        complexity = commit["complexity_score"]

        for _, test in selected_tests.iterrows():
            base_prob = BASE_FAILURE_RATE

            # module-level risk signal
            primary_mod = test["primary_module"]
            primary_bug_count = module_risk.get(primary_mod, 0.0)
            primary_norm = primary_bug_count / (module_risk.max() + 1e-6)

            # combine module risk
            risk_signal = (module_risk_norm + primary_norm) / 2.0
            mod_factor = 1.0 + risk_signal * (HIGH_RISK_MODULE_MULTIPLIER - 1.0)

            author_factor = 1.0 + author_is_junior * (JUNIOR_AUTHOR_MULTIPLIER - 1.0)
            complexity_factor = 1.0 + complexity * (RUNTIME_FAILURE_MULTIPLIER - 1.0)

            # tests that are historically fragile will fail a bit more
            hist_pass = test["historical_pass_rate"]
            frag_factor = 1.0 + (1.0 - hist_pass) * 2.0

            p_fail = base_prob * mod_factor * author_factor * complexity_factor * frag_factor
            p_fail = float(np.clip(p_fail, 0.01, 0.9))

            passed = rng.random() > p_fail

            sim_time = max(
                1.0,
                rng.normal(test["typical_runtime_seconds"], test["typical_runtime_seconds"] * 0.1),
            )

            rows.append(
                {
                    "commit_id": commit["commit_id"],
                    "test_id": test["test_id"],
                    "module_id": primary_mod,
                    "passed": int(passed),
                    "sim_time_seconds": sim_time,
                }
            )

    verif_df = pd.DataFrame(rows)
    return verif_df


def generate_authors_for_lookup(commits_df: pd.DataFrame) -> pd.DataFrame:
    """Generate a consistent author table and return indexed by author_id."""
    unique_authors = commits_df["author_id"].unique()
    # Reuse logic from generate_authors but restricted to known authors
    full_authors = generate_authors(len(unique_authors))
    full_authors["author_id"] = unique_authors
    return full_authors.set_index("author_id")


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True, parents=True)

    modules_df = generate_modules(NUM_MODULES)
    authors_df = generate_authors(NUM_AUTHORS)
    commits_df = generate_commits(NUM_COMMITS, modules_df, authors_df)
    tests_df = generate_tests(NUM_TESTS, modules_df)
    # Pass the canonical authors_df so DGP uses the SAME experience scores
    # that are stored in commits.csv — fixing the author signal leakage bug.
    verif_df = generate_verification_results(commits_df, modules_df, tests_df, authors_df)

    modules_df.to_csv(MODULES_CSV, index=False)
    authors_df.to_csv(DATA_DIR / "authors.csv", index=False)
    commits_df.to_csv(COMMITS_CSV, index=False)
    tests_df.to_csv(TESTS_CSV, index=False)
    verif_df.to_csv(VERIF_RESULTS_CSV, index=False)

    print(f"Wrote synthetic data to {DATA_DIR}")


if __name__ == "__main__":
    main()

