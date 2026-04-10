# 🐛 RTL Bug Analyzer - Log Analysis & Triage System

An AI-powered system to analyze RTL verification logs, extract unique failure signatures, classify bugs by priority, and generate a ranked triage list for engineering teams.

## 🎯 Overview

This system automates the tedious process of:
1. **Parsing** verification logs from failed test runs
2. **Extracting** unique failure signatures and patterns
3. **Classifying** bugs by severity, impact, and complexity
4. **Prioritizing** which bugs to fix first
5. **Estimating** effort and timeline for fixes

**Key Benefit**: Turn overwhelming failure logs into a clear, actionable prioritized bug list that engineers can tackle in order.

## 🏗️ Project Structure

```
rtl_bug_analyzer/
├── scripts/
│   ├── __init__.py
│   ├── log_parser.py              # Parse logs and extract signatures
│   ├── bug_classifier.py           # Classify and prioritize bugs
│   └── run_pipeline.py             # Main execution pipeline
├── dashboard/
│   └── app.py                      # Streamlit visualization dashboard
├── data/
│   ├── verification_run_001.log    # Input: Raw verification logs
│   ├── bug_triage_list.csv         # Output: Prioritized bug list
│   └── triage_plan.json            # Output: Detailed triage plan
├── models/
│   └── (future ML models)
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Analysis Pipeline

```bash
cd scripts
python run_pipeline.py
```

This will:
- Parse all `.log` files in `data/` (supports `TEST=` and `FAILURES=` tags)
- Extract unique failure signatures along with category (UVM/SVA/GENERAL)
- Compute recurrence counts and testcase impact
- Classify bugs by priority (recurrence × testcase impact by default)
- Generate categorized summaries and show recent git changes per module
- Display debug hints and highlight the top bug to work on
- Save prioritized bug list to CSV

### 3. View Interactive Dashboard

```bash
cd dashboard
streamlit run app.py
```

Visit **http://localhost:8501** to explore:
- 📊 **Overview** - KPI cards, distribution charts, timeline estimates
- 📋 **Triage List** - Filterable table of all bugs with priority scores, test case impact, categories
- 📈 **Analysis** - Detailed breakdowns by failure type, module, complexity
- 🎯 **Fix Plan** - Recommended sprint schedule and effort estimates

## 📊 How It Works

### Step 1: Log Parsing
- Scans verification logs for failure keywords (ERROR, FAIL, ASSERT, TIMEOUT, etc.)
- Extracts timestamp, module, category (UVM/SVA/GENERAL), severity
- Reads `TEST=` and `FAILURES=` tags to capture testcase IDs and counts
- Groups related failures into unique signatures

**Example log entry:**
```
2026-03-06 15:30:45 [AHB_Controller] TEST=test_ahb_001 FAILURES=5 ERROR: Assertion failure in handshake protocol
```

**Extracted signature:**
```
Failure Type: assertion_failure
Category: SVA
Module: AHB_Controller
Severity: HIGH
Occurrence Count: 5
Testcase Impact: 1
Total Failures: 5
```

### Step 2: Bug Classification

By default, priority is calculated from:

- **Recurrence Count** – how many log lines match the signature
- **Testcase Impact** – number of distinct tests that hit the failure

Alternative scoring functions (severity/impact/complexity) can be added easily in `bug_classifier.py`.

**Default Priority Score = Recurrence × Testcase Impact**

### Step 3: Impact & Change Analysis

- **Categorized summary**: counts by error category and by affected module
- **Recent changes**: runs `git log` to show the last few commits mentioning each module (if repository is a git repo)
- **Debug hints**: simple mapping from failure type to suggested starting points

The CLI output highlights the top-scoring bug and prints debug tips oriented to the failure type.

### Step 4: Triage Planning

Bugs are ordered by priority score and written to `data/bug_triage_list.csv` for downstream tools.

Priority levels are still applied (CRITICAL/HIGH/MEDIUM/LOW) if you add a weighted scoring rule.

## 📈 Example Output

### Command Line Report

```
================================================================================
RTL BUG ANALYZER - Log Analysis & Triage System
================================================================================

📊 Statistics:
  Total Bugs Found:      15
  🔴 Critical Priority:  3
  🟠 High Priority:      5
  🟡 Medium Priority:    4
  🟢 Low Priority:       3

⏱️  Estimated Fix Time:
  Total Hours:   78
  Total Days:    10
  Total Weeks:   2

================================================================================
PRIORITIZED BUG LIST (Top 20)
================================================================================

 1. 🔴 [CRITICAL] Score: 4.65
    Module: Memory_Controller
    Type: data_corruption
    Occurrences: 8 | Complexity: Very High

 2. 🔴 [CRITICAL] Score: 4.52
    Module: AHB_Controller
    Type: assertion_failure
    Occurrences: 6 | Complexity: High

 3. 🟠 [HIGH] Score: 3.85
    Module: Interconnect
    Type: deadlock
    Occurrences: 4 | Complexity: Very High
...
```

### CSV Output (`bug_triage_list.csv`)

| signature_id | failure_type | module | occurrence_count | priority_score | priority_level | complexity | severity |
|---|---|---|---|---|---|---|---|
| 1 | data_corruption | Memory_Controller | 8 | 4.65 | CRITICAL | Very High | CRITICAL |
| 2 | assertion_failure | AHB_Controller | 6 | 4.52 | CRITICAL | High | HIGH |
| 3 | deadlock | Interconnect | 4 | 3.85 | HIGH | Very High | HIGH |
| ... | ... | ... | ... | ... | ... | ... | ... |

### JSON Output (`triage_plan.json`)

```json
{
  "total_bugs": 15,
  "critical_count": 3,
  "high_count": 5,
  "medium_count": 4,
  "low_count": 3,
  "estimated_fix_time": {
    "total_hours": 78,
    "total_days": 10,
    "total_weeks": 2
  },
  "triage_by_priority": {
    "CRITICAL": [
      {
        "signature_id": 1,
        "failure_type": "data_corruption",
        "module": "Memory_Controller",
        "occurrence_count": 8,
        "complexity": "Very High",
        "estimated_hours": 16
      },
      ...
    ],
    ...
  }
}
```

## 🔍 Supported Failure Types

- **assertion_failure** - Test assertion violations
- **timeout** - Test/operation timeouts
- **illegal_state** - Invalid FSM/state machine states
- **deadlock** - System deadlocks/no progress
- **data_corruption** - Data mismatches or corruption
- **clock_issue** - Clock domain crossing problems
- **reset_issue** - Reset sequence failures
- **interface_error** - Protocol/handshake violations
- **memory_error** - Memory access violations
- **cache_error** - Cache coherency issues
- **arbitration** - Arbitration/grant failures
- **coverage** - Coverage point violations

## 🎯 Key Modules & Priority Scoring

### Critical Modules (Score 4-5)
- `Memory_Controller` - Core memory subsystem
- `AHB_Controller` - Main bus controller
- `Interconnect` - System interconnect
- `Clock_Domain` - Clock domain crossings
- `Reset_Logic` - Reset sequence controller

### High-Impact Modules (Score 2-3)
- `Cache_L1`, `Cache_L2` - Cache subsystems
- `Data_Path` - Data processing pipeline
- `Control_Unit` - Control logic
- `Register_File` - Register storage

### Standard Modules (Score 1-2)
- `ALU`, `SPI_Interface`, `I2C_Interface`, `UART_Controller`, `GPIO_Controller`

## 💡 Use Cases

1. **Daily Triage** - After each test run, automatically generate priority bug list
2. **Sprint Planning** - Estimate effort and velocity for fixing classified bugs
3. **Resource Allocation** - Assign engineers based on complexity scores
4. **Milestone Tracking** - Monitor progress against triage timeline
5. **Root Cause Analysis** - Identify patterns (e.g., 60% of bugs in Memory_Controller)

## 🛠️ Future Enhancements

- [ ] Machine learning classification model (train on historical bugs)
- [ ] Slack/Email notifications for critical bugs
- [ ] Integration with Jira for automated ticket creation
- [ ] Root cause correlations (e.g., "Bugs spike after Feature X commit")
- [ ] Predictive model: "This module likely to fail"
- [ ] Cross-correlation with code changes (git integration)

## 📝 Log Format

Logs should contain lines with these patterns:

```
[TIMESTAMP] [MODULE] SEVERITY: MESSAGE

Examples:
2026-03-06 15:30:45 [AHB_Controller] ERROR: Assertion failure in handshake
2026-03-06 15:31:12 [Memory_Controller] FATAL: Data corruption detected
```

If logs don't follow this format, extend the `LogParser` class in `log_parser.py` to handle your specific format.

## 📊 Dashboard Features

### 📊 Overview Tab
- KPI cards (total bugs, critical count, avg priority score)
- Priority distribution pie chart
- Most affected modules bar chart
- Time estimate breakdown (hours, days, weeks)

### 📋 Triage List Tab
- Filterable bug table by priority, module, complexity
- Full bug details and scores
- Sortable columns

### 📈 Analysis Tab
- Failure type distribution
- Priority score distribution histogram
- Complexity vs priority scatter plot
- Module impact analysis (bug count + avg priority)

### 🎯 Fix Plan Tab
- Bugs grouped by priority level
- Recommended sprint schedule
- Effort estimates per priority
- Calendar timeline

## ⚡ Performance

- **Parsing**: ~1000 log lines per second
- **Classification**: ~100 bugs per second
- **Dashboard**: Loads <1 second for 50+ bugs

## 📄 License

Internal Use Only - SandiskAI RTL Verification Tools