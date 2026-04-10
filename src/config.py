from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

# Directories
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

DATA_DIR.mkdir(exist_ok=True, parents=True)
MODELS_DIR.mkdir(exist_ok=True, parents=True)


# Synthetic data sizes / knobs
NUM_MODULES = 80
NUM_AUTHORS = 20
NUM_TESTS = 150
NUM_COMMITS = 5000

# Synthetic behavior knobs
BASE_FAILURE_RATE = 0.03  # baseline failure probability
HIGH_RISK_MODULE_MULTIPLIER = 4.0
JUNIOR_AUTHOR_MULTIPLIER = 1.8
COMPLEXITY_MULTIPLIER = 2.0
RUNTIME_FAILURE_MULTIPLIER = 1.3

# CI / ROI knobs
DEFAULT_DOLLAR_PER_COMPUTE_HOUR = 2.0
TOP_RISK_PERCENT_FOR_FRONTLOADING = 0.2


# File paths
COMMITS_CSV = DATA_DIR / "commits.csv"
MODULES_CSV = DATA_DIR / "modules.csv"
TESTS_CSV = DATA_DIR / "tests.csv"
VERIF_RESULTS_CSV = DATA_DIR / "verif_results.csv"

MODEL_PATH = MODELS_DIR / "test_failure_model.pkl"
