# SanDisk AI RTL Verification System

A comprehensive AI-driven RTL verification system with React frontend dashboard.

## Architecture

- **Backend**: Python ML pipeline for RTL verification failure prediction
- **API**: Flask REST API serving data to frontend
- **Frontend**: React dashboard with RTL module heatmap and test prioritization

## Quick Start

1. **Run the ML Pipeline**:
   ```bash
   cd rtl_verification_system
   python run_pipeline.py
   ```
   This generates data, trains models, and starts the API server.

2. **Start the React Frontend**:
   ```bash
   cd "sandisk front end"
   npm install
   npm run dev
   ```

3. **Access the Dashboard**:
   - React Dashboard: http://localhost:5173/
   - API Endpoints: http://localhost:5000/api/*

## API Endpoints

- `GET /api/overview` - Dashboard KPIs and metrics
- `GET /api/test-queue` - Test prioritization data
- `GET /api/heatmap` - Module risk heatmap data
- `GET /api/model-insights` - ML model performance
- `GET /api/roi-analysis` - Cost savings analysis

## Features

- **RTL Module Heatmap**: Interactive SoC floorplan showing risk levels
- **Test Prioritization**: AI-ranked test queue based on failure probability
- **Real-time Metrics**: Cost savings, time-to-first-failure reduction
- **Model Insights**: ROC-AUC, feature importance, performance metrics

## Data Flow

1. Python pipeline generates synthetic RTL verification data
2. XGBoost model trained on historical failure patterns
3. Model predicts failure probabilities for new commits
4. Tests prioritized by risk score
5. Flask API serves data to React frontend
6. Interactive dashboard displays results with module heatmap

## Module Heatmap

The RTL block heatmap visualizes:
- Risk-weighted module coloring (green=low, yellow=medium, red=high)
- Interactive selection and details
- Failure clustering by module
- Lines of code and commit frequency