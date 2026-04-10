# AI-Driven EDA Regression Optimizer

An intelligent system that optimizes RTL (Register-Transfer Level) verification regressions in ASIC/SoC design by using machine learning to predict test failure probabilities and prioritize high-risk tests, significantly reducing time-to-first-failure and compute costs.

## Problem

RTL verification consumes up to 70% of ASIC/SoC development schedules. Traditional brute-force regression testing runs thousands of tests on every commit, wasting compute resources and delaying feedback on critical bugs.

## Solution

This AI-driven prediction engine analyzes commit data, module attributes, and historical test outcomes to score each test's failure probability for new commits. It then reorders regression queues to front-load the highest-risk tests, enabling earlier bug discovery and more efficient resource utilization.

## Features

- **Predictive Modeling**: XGBoost-based classifier trained on synthetic historical data to predict test failure probabilities
- **Risk-Based Prioritization**: Automatically reorders test suites by predicted failure risk
- **Interactive Dashboard**: Streamlit-based visualization showing:
  - Module risk heatmaps
  - Test prioritization rankings
  - ROI analysis (time and cost savings)
  - Real-time scoring for new commits
- **Data Pipeline**: Comprehensive feature engineering from commits, modules, tests, and verification results
- **CI/CD Integration**: Designed for drop-in integration with existing EDA tooling and CI pipelines
- **Oracle Diagnostics**: Built-in evaluation tools to assess model performance against theoretical best-case scenarios

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-eda-regression-optimizer.git
   cd ai-eda-regression-optimizer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Generate synthetic data (if needed):
   ```bash
   python src/data_generator.py
   ```

4. Train the model:
   ```bash
   python src/train_model.py
   ```

## Usage

### Running the Dashboard
```bash
streamlit run src/dashboard_app.py
```

The dashboard provides interactive visualization of risk predictions, test prioritization, and ROI metrics.

### Scoring a New Commit
Use the CI simulator to prioritize tests for a specific commit:
```python
from src.ci_simulator import prioritize_tests_for_commit
prioritized_tests = prioritize_tests_for_commit(commit_id="your_commit_id")
```

### Diagnostics
Run oracle diagnostics to evaluate model performance:
```bash
python oracle_diag.py
```

## Project Structure

```
├── data/                    # Synthetic datasets (CSV files)
│   ├── authors.csv
│   ├── commits.csv
│   ├── modules.csv
│   ├── tests.csv
│   └── verif_results.csv
├── models/                  # Trained model artifacts
├── pitch_deck/             # Business presentation materials
│   └── outline.md
├── src/                    # Source code
│   ├── ci_simulator.py     # Core simulation and prioritization logic
│   ├── config.py           # Configuration constants
│   ├── dashboard_app.py    # Streamlit dashboard
│   ├── data_generator.py   # Synthetic data generation
│   ├── debug_prioritizer.py # Debugging utilities
│   ├── features.py         # Feature engineering
│   └── train_model.py      # Model training pipeline
├── oracle_diag.py          # Performance diagnostics
├── requirements.txt        # Python dependencies
└── README.md
```

## Architecture

- **Data Ingestion**: Processes version control, bug tracking, and verification log data
- **Feature Engineering**: Extracts signals from commit attributes, module complexity, author experience, and historical performance
- **ML Model**: XGBoost classifier outputting failure probabilities per (commit, test) pair
- **Optimization Engine**: Reorders regression queues based on risk scores
- **Visualization**: Real-time dashboard for monitoring and analysis

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## License

This project is open-source. Please check the license file for details.