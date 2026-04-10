# RTL Bug Analyzer - Project Setup & Usage

## Project Overview
RTL Bug Analyzer is an AI-powered system to analyze RTL verification logs, extract unique failure signatures, classify bugs by priority, and generate a ranked triage list for engineering teams.

## Project Structure
```
rtl_bug_analyzer/
├── scripts/
│   ├── log_parser.py           # Parse logs and extract signatures
│   ├── bug_classifier.py       # Classify and prioritize bugs
│   └── run_pipeline.py         # Main execution pipeline
├── dashboard/
│   └── app.py                  # Streamlit visualization
├── data/                       # Input logs and output results
├── models/                     # Future ML models
├── requirements.txt            # Python dependencies
└── README.md                   # Detailed documentation
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Analysis Pipeline
```bash
cd scripts
python run_pipeline.py
```

This will:
- Parse verification logs from `data/` directory
- Extract unique failure signatures
- Classify bugs by priority (CRITICAL, HIGH, MEDIUM, LOW)
- Generate triage results (CSV and JSON)
- Display prioritized bug list in console

### 3. View Dashboard
```bash
cd dashboard
streamlit run app.py
```

Navigate to **http://localhost:8501** for interactive visualization.

## Key Components

### LogParser (`scripts/log_parser.py`)
- Scans verification logs for failure patterns
- Extracts timestamp, module, failure type, severity
- Groups related failures into unique signatures
- Supports 12 failure types: assertion_failure, timeout, deadlock, data_corruption, etc.

### BugClassifier (`scripts/bug_classifier.py`)
- Scores bugs based: severity (40%), module impact (30%), frequency (20%), complexity (10%)
- Assigns priority levels: CRITICAL (≥4.0), HIGH (≥3.0), MEDIUM (≥2.0), LOW (<2.0)
- Estimates fix time per bug and generates triage timeline

### Dashboard (`dashboard/app.py`)
Streamlit app with 4 tabs:
- **📊 Overview** - KPI cards, distribution charts, timeline
- **📋 Triage List** - Filterable bug table with priority scores
- **📈 Analysis** - Detailed breakdowns by type, module, complexity
- **🎯 Fix Plan** - Recommended sprint schedule and effort estimates

## Outputs

### bug_triage_list.csv
Prioritized list of all identified bugs with scores and metadata

| signature_id | failure_type | module | occurrences | priority_score | priority_level | complexity |
|---|---|---|---|---|---|---|
| 1 | data_corruption | Memory_Controller | 2 | 4.10 | CRITICAL | Very High |
| 2 | assertion_failure | AHB_Controller | 2 | 2.80 | MEDIUM | Medium |

### triage_plan.json
Detailed triage plan grouped by priority with effort estimates and timeline

## Log Format

Logs should contain failure indicators in lines like:

```
[TIMESTAMP] [MODULE] SEVERITY: MESSAGE

Examples:
2026-03-06 15:30:45 [AHB_Controller] ERROR: Assertion failure in handshake
2026-03-06 15:31:12 [Memory_Controller] FATAL: Data corruption detected
```

## Module Priority Scoring

**Critical (4-5 points):** Memory_Controller, AHB_Controller, Interconnect, Clock_Domain, Reset_Logic
**High (2-3 points):** Cache_L1, Cache_L2, Data_Path, Control_Unit, Register_File
**Standard (1-2 points):** ALU, SPI_Interface, I2C_Interface, UART_Controller, GPIO_Controller

## Failure Types Detected

- assertion_failure - Test assertion violations
- timeout - Test/operation timeouts
- illegal_state - Invalid FSM states
- deadlock - System deadlocks
- data_corruption - Data mismatches
- clock_issue - Clock domain crossing problems
- reset_issue - Reset sequence failures
- interface_error - Protocol violations
- memory_error - Memory access violations
- cache_error - Cache coherency issues
- arbitration - Arbitration failures
- coverage - Coverage point violations

## Development Notes

### Adding Support for New Log Format
Edit `LogParser._extract_module()` and `LogParser._is_failure_line()` in `log_parser.py`

### Adjusting Priority Calculation Weights
Modify `BugClassifier.__init__()` severity_weights, impact_scores, complexity_factors dicts

### Adding New Failure Types
Update `LogParser.failure_patterns` regex dictionary with new patterns

## Performance
- Parsing: ~1000 log lines/second
- Classification: ~100 bugs/second
- Dashboard loads: <1 second for 50+ bugs

## Future Enhancements
- [ ] ML classification model trained on historical bugs
- [ ] Slack/Email notifications for critical bugs
- [ ] Jira integration for automated ticket creation
- [ ] Root cause correlation analysis
- [ ] Git integration for code change correlation
- [ ] Predictive failure model

## Testing
The system includes a synthetic log generator. Run without log files to auto-generate test data:
```bash
cd scripts
python run_pipeline.py  # Auto-generates verification_run_001.log
```

## Support
For issues or feature requests, refer to the main README.md or contact the development team.
