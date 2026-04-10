"""
Flask API server for RTL Verification System
Serves data to the React frontend dashboard
"""

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
import traceback
import joblib

app = Flask(__name__)
# Enable CORS for React frontend with wildcard
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"])

# Get the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Hardcoded model directory (user-specified) ─────────────────────────────────
MODELS_DIR = r"C:\Users\flame\Documents\SandiskAI\rtl_verification_system\models"


@app.route('/api/model-status')
def model_status():
    """Confirm the XGBoost model loads correctly and run a real test prediction."""
    model_path  = os.path.join(MODELS_DIR, 'rtl_predictor_model.pkl')
    scaler_path = os.path.join(MODELS_DIR, 'scaler.pkl')
    feat_path   = os.path.join(MODELS_DIR, 'feature_cols.pkl')

    exists = {
        'model' : os.path.exists(model_path),
        'scaler': os.path.exists(scaler_path),
        'features': os.path.exists(feat_path),
    }

    if not all(exists.values()):
        return jsonify({'status': 'ERROR', 'exists': exists,
                        'message': 'One or more model files are missing.'}), 500

    try:
        model        = joblib.load(model_path)
        scaler       = joblib.load(scaler_path)
        feature_cols = joblib.load(feat_path)

        # Run one low-risk and one high-risk dummy prediction to verify
        test_cases = [
            {'label': 'low_risk',  'vec': [15, 2, 12, 5, 1, 0.1, 0, 0.05, 0.6, 0, 0.2,  0.025, 0.1]},
            {'label': 'high_risk', 'vec': [0, 40, 480, 240, 12, 0.9, 1, 0.9, 12.0, 1, 36.0, 0.069, 0.95]},
        ]
        results = {}
        for tc in test_cases:
            X = np.array([tc['vec']])
            X_s = scaler.transform(X)
            prob = float(model.predict_proba(X_s)[0][1])
            results[tc['label']] = {'failure_prob': round(prob, 4), 'risk_score': round(prob * 100, 1)}

        mtime    = os.path.getmtime(model_path)
        model_ts = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

        print(f"[model-status] Model OK — low={results['low_risk']['risk_score']} high={results['high_risk']['risk_score']}")
        return jsonify({
            'status':        'OK',
            'model_path':    model_path,
            'feature_cols':  feature_cols,
            'model_trained': model_ts,
            'file_sizes_kb': {
                'model':  round(os.path.getsize(model_path)  / 1024, 1),
                'scaler': round(os.path.getsize(scaler_path) / 1024, 1),
            },
            'test_predictions': results,
            'sanity_check': (
                'PASS' if results['high_risk']['risk_score'] > results['low_risk']['risk_score']
                else 'FAIL — high-risk score not higher than low-risk!'
            ),
        })
    except Exception as e:
        return jsonify({'status': 'ERROR', 'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'API server is running'})

@app.route('/api/overview')
def get_overview():
    """Get dashboard overview data"""
    try:
        # Load data with absolute paths
        df_history = pd.read_csv(os.path.join(BASE_DIR, 'data/rtl_verification_history.csv'))
        df_recent = pd.read_csv(os.path.join(BASE_DIR, 'data/recent_commits.csv'))
        df_optimized = pd.read_csv(os.path.join(BASE_DIR, 'data/optimized_test_queue.csv'))

        with open(os.path.join(BASE_DIR, 'data/optimization_impact.json'), 'r') as f:
            impact = json.load(f)

        with open(os.path.join(BASE_DIR, 'models/model_metadata.json'), 'r') as f:
            metadata = json.load(f)

        # Calculate metrics
        failure_rate = df_history['test_failed'].mean() * 100
        risk_dist = pd.cut(df_optimized['risk_score'],
                          bins=[0, 33, 66, 100],
                          labels=['Low', 'Medium', 'High']).value_counts()

        return jsonify({
            'kpis': {
                'regression_time_saved': impact['time_saved_hours'],
                'cost_savings': impact['cost_saved_usd'],
                'model_accuracy': metadata['roc_auc_score'],
                'failures_detected_early': impact['failure_catch_rate_percent']
            },
            'failure_rate': failure_rate,
            'risk_distribution': risk_dist.to_dict(),
            'total_commits': len(df_history),
            'recent_commits': len(df_recent)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-queue')
def get_test_queue():
    """Get test queue analysis data"""
    try:
        df_optimized = pd.read_csv(os.path.join(BASE_DIR, 'data/optimized_test_queue.csv'))

        # Risk quartiles
        df_copy = df_optimized.copy()
        df_copy['risk_quartile'] = pd.qcut(
            df_copy['risk_score'], q=4,
            duplicates='drop'
        )
        # Convert quartile labels to strings for JSON serialization
        df_copy['risk_quartile'] = df_copy['risk_quartile'].astype(str)
        failure_by_quartile = df_copy.groupby('risk_quartile')['predicted_failure_probability'].agg(['mean', 'std', 'count'])

        # Add risk level
        df_optimized['risk_level'] = pd.cut(df_optimized['risk_score'],
                                           bins=[0, 33, 66, 100],
                                           labels=['Low', 'Medium', 'High'])

        return jsonify({
            'queue_stats': {
                'mean_risk': df_optimized['risk_score'].mean(),
                'median_risk': df_optimized['risk_score'].median(),
                'max_risk': df_optimized['risk_score'].max(),
                'min_risk': df_optimized['risk_score'].min()
            },
            'failure_by_quartile': failure_by_quartile.reset_index().to_dict('records'),
            'test_queue': df_optimized.to_dict('records')  # All records — sorted by risk_score desc
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/heatmap')
def get_heatmap():
    """Get module risk heatmap data"""
    try:
        df_optimized = pd.read_csv(os.path.join(BASE_DIR, 'data/optimized_test_queue.csv'))

        # Extract module risks
        module_risks = {}
        for _, row in df_optimized.iterrows():
            modules = row['modules_affected'].split(',')
            for module in modules:
                module = module.strip()
                if module not in module_risks:
                    module_risks[module] = {
                        'count': 0,
                        'total_risk': 0,
                        'total_failure_prob': 0
                    }
                module_risks[module]['count'] += 1
                module_risks[module]['total_risk'] += row['risk_score']
                module_risks[module]['total_failure_prob'] += row['predicted_failure_probability']

        # Calculate average risk per module
        module_stats = []
        for module, stats in module_risks.items():
            module_stats.append({
                'module': module,
                'avg_risk_score': stats['total_risk'] / stats['count'],
                'avg_failure_prob': stats['total_failure_prob'] / stats['count'],
                'commit_count': stats['count'],
            })

        module_df = pd.DataFrame(module_stats).sort_values('avg_risk_score', ascending=False)

        # Module layout for floorplan
        module_layout = {
            'Memory_Controller': {'x': 0, 'y': 0, 'w': 2, 'h': 2},
            'Cache_L1': {'x': 2, 'y': 0, 'w': 1.5, 'h': 2},
            'Cache_L2': {'x': 3.5, 'y': 0, 'w': 1.5, 'h': 2},
            'AHB_Controller': {'x': 0, 'y': 2, 'w': 2, 'h': 1.5},
            'Interconnect': {'x': 2, 'y': 2, 'w': 3, 'h': 1.5},
            'ALU': {'x': 0, 'y': 3.5, 'w': 1.5, 'h': 1.5},
            'Control_Unit': {'x': 1.5, 'y': 3.5, 'w': 1.5, 'h': 1.5},
            'Data_Path': {'x': 3, 'y': 3.5, 'w': 2.5, 'h': 1.5},
            'Register_File': {'x': 5.5, 'y': 3.5, 'w': 1, 'h': 1.5},
            'SPI_Interface': {'x': 0, 'y': 5, 'w': 1.3, 'h': 1},
            'I2C_Interface': {'x': 1.3, 'y': 5, 'w': 1.3, 'h': 1},
            'UART_Controller': {'x': 2.6, 'y': 5, 'w': 1.4, 'h': 1},
            'GPIO_Controller': {'x': 4, 'y': 5, 'w': 1.5, 'h': 1},
            'Clock_Domain': {'x': 5.5, 'y': 5, 'w': 1, 'h': 1},
            'Reset_Logic': {'x': 6.5, 'y': 5, 'w': 1, 'h': 1},
        }

        # Add layout info to modules
        for stat in module_stats:
            module = stat['module']
            if module in module_layout:
                stat['layout'] = module_layout[module]

        return jsonify({
            'modules': module_stats,
            'layout': module_layout
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/model-insights')
def get_model_insights():
    """Get model insights and metadata"""
    try:
        with open(os.path.join(BASE_DIR, 'models/model_metadata.json'), 'r') as f:
            metadata = json.load(f)

        return jsonify(metadata)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/roi-analysis')
def get_roi_analysis():
    """Get ROI analysis data"""
    try:
        with open(os.path.join(BASE_DIR, 'data/optimization_impact.json'), 'r') as f:
            impact = json.load(f)

        return jsonify(impact)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/predictor', methods=['POST'])
def predict_failure():
    """Interactive failure predictor — loads the latest model from disk on every call."""
    try:
        data = request.json

        # ── Parse the 5 core user inputs ────────────────────────────────────────
        code_churn_ratio         = float(data.get('code_churn_ratio', 0.5))
        files_modified           = int(data.get('files_modified', 10))
        author_experience_years  = int(data.get('author_experience_years', 5))
        historical_bug_frequency = float(data.get('historical_bug_frequency', 0.3))
        modules_affected_count   = int(data.get('modules_affected_count', 3))
        is_hotspot_module        = int(data.get('is_hotspot_module', 0))
        has_critical_module      = int(data.get('has_critical_module', 0))

        # ── Derived features — use pre-computed values from CLI if provided ──────
        lines_added           = int(data.get('lines_added',
                                   int(code_churn_ratio * files_modified * 15)))
        lines_deleted         = int(data.get('lines_deleted',
                                   int(code_churn_ratio * files_modified * 8)))
        regression_time_hours = float(data.get('regression_time_hours',
                                   max(0.5, files_modified * 0.3)))
        code_churn_normalized = float(data.get('code_churn_normalized',
                                   code_churn_ratio * files_modified))
        bug_density           = float(data.get('bug_density',
                                   historical_bug_frequency / (modules_affected_count + 1)))
        risk_score_raw        = float(data.get('risk_score', (
            (1 - author_experience_years / 20) * 0.2 +
            code_churn_ratio * 0.3 +
            is_hotspot_module * 0.2 +
            (bug_density / (bug_density if bug_density > 0 else 1e-9)) * 0.3
        )))


        # ── Load latest model fresh from disk (exact path) ──────────────────────
        model_path  = os.path.join(MODELS_DIR, 'rtl_predictor_model.pkl')
        scaler_path = os.path.join(MODELS_DIR, 'scaler.pkl')
        feat_path   = os.path.join(MODELS_DIR, 'feature_cols.pkl')
        print(f"[predictor] Model path: {model_path}")
        print(f"[predictor] Exists: model={os.path.exists(model_path)} scaler={os.path.exists(scaler_path)} feat={os.path.exists(feat_path)}")

        model_loaded = (
            os.path.exists(model_path) and
            os.path.exists(scaler_path) and
            os.path.exists(feat_path)
        )

        if model_loaded:
            model       = joblib.load(model_path)
            scaler      = joblib.load(scaler_path)
            feature_cols = joblib.load(feat_path)

            feature_vector = {
                'author_experience_years':  author_experience_years,
                'files_modified':           files_modified,
                'lines_added':              lines_added,
                'lines_deleted':            lines_deleted,
                'modules_affected_count':   modules_affected_count,
                'code_churn_ratio':         code_churn_ratio,
                'is_hotspot_module':        is_hotspot_module,
                'historical_bug_frequency': historical_bug_frequency,
                'regression_time_hours':    regression_time_hours,
                'has_critical_module':      has_critical_module,
                'code_churn_normalized':    code_churn_normalized,
                'bug_density':              bug_density,
                'risk_score':               risk_score_raw,
            }
            X            = np.array([[feature_vector[col] for col in feature_cols]])
            X_scaled     = scaler.transform(X)
            failure_prob = float(model.predict_proba(X_scaled)[0][1])
            risk_score   = round(failure_prob * 100, 1)
            source       = 'xgboost_model'

            # Include model timestamp so frontend can confirm which model was used
            try:
                mtime = os.path.getmtime(model_path)
                model_ts = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
            except Exception:
                model_ts = 'unknown'
        else:
            # Fallback: model files missing
            risk_score   = max(0, min(100, risk_score_raw * 100))
            failure_prob = risk_score / 100 * 0.5 + 0.1
            source       = 'formula_fallback'
            model_ts     = 'N/A'

        risk_level = 'HIGH' if risk_score > 70 else 'MEDIUM' if risk_score > 40 else 'LOW'

        recommendation_map = {
            'HIGH':   'High failure risk. Run full regression suite and request a senior RTL review before merge.',
            'MEDIUM': 'Moderate risk. Run targeted regression on affected modules and verify timing constraints.',
            'LOW':    'Low risk change. Standard smoke-test regression is sufficient before merge.',
        }

        return jsonify({
            'risk_score':          round(risk_score, 1),
            'failure_probability': round(failure_prob, 4),
            'risk_level':          risk_level,
            'recommendation':      recommendation_map[risk_level],
            'prediction_source':   source,
            'model_timestamp':     model_ts,
            'feature_vector':      feature_vector if model_loaded else {},
        })
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/raw-optimized-csv')
def raw_optimized_csv():
    """Return the raw optimized_test_queue.csv file so the front end can parse it directly."""
    try:
        csv_path = os.path.join(BASE_DIR, 'data', 'optimized_test_queue.csv')
        return send_file(csv_path, mimetype='text/csv')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found', 'path': request.path}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

if __name__ == '__main__':
    print(f"Starting API server from {BASE_DIR}")
    print("Checking data files...")
    for fname in ['data/rtl_verification_history.csv', 'data/optimized_test_queue.csv', 'models/model_metadata.json']:
        fpath = os.path.join(BASE_DIR, fname)
        exists = os.path.exists(fpath)
        print(f"  {fname}: {'✓' if exists else '✗'}")
    print("\nStarting Flask app on http://localhost:5000")
    print("Available endpoints:")
    print("  GET  /api/health")
    print("  GET  /api/overview")
    print("  GET  /api/test-queue")
    print("  GET  /api/heatmap")
    print("  GET  /api/model-insights")
    print("  GET  /api/roi-analysis")
    print("  POST /api/predictor")
    app.run(debug=False, port=5000, host='0.0.0.0')