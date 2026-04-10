"""
CI/CD Test Reordering Optimizer
Intercepts regression queue and prioritizes tests based on ML failure predictions
"""

import pandas as pd
import numpy as np
import joblib
import json
from datetime import datetime
from sklearn.preprocessing import StandardScaler
import os


class TestQueueOptimizer:
    """
    Optimizer for RTL verification test queue
    Uses ML model to predict failure probability and reorder tests
    """
    
    def __init__(self, model_path='models/rtl_predictor_model.pkl',
                 scaler_path='models/scaler.pkl',
                 feature_cols_path='models/feature_cols.pkl'):
        """Load pre-trained model and artifacts"""
        
        print("[Initializing Test Queue Optimizer]")
        
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        self.feature_cols = joblib.load(feature_cols_path)
        
        # Load metadata
        with open('models/model_metadata.json', 'r') as f:
            self.metadata = json.load(f)
        
        print(f"✓ Model loaded (ROC-AUC: {self.metadata['roc_auc_score']:.4f})")
        print(f"✓ Expected features: {len(self.feature_cols)}")
    
    def predict_failure_probability(self, commit_df):
        """
        Predict failure probability for a commit
        
        Args:
            commit_df: DataFrame with single commit record
            
        Returns:
            failure_probability: Float between 0 and 1
            risk_score: Composite risk metric
        """
        
        # Preprocess commit data
        processed_df = self._preprocess_commit(commit_df.copy())
        
        # Extract features
        X = processed_df[self.feature_cols]
        
        # Scale
        X_scaled = self.scaler.transform(X)
        
        # Predict
        failure_prob = self.model.predict_proba(X_scaled)[0, 1]
        
        # Calculate composite risk score (0-100)
        risk_components = processed_df[['code_churn_ratio', 'is_hotspot_module', 
                                        'bug_density', 'code_churn_normalized']].iloc[0]
        risk_score = (
            failure_prob * 60 +  # ML prediction is main factor
            risk_components['code_churn_ratio'] * 15 +
            risk_components['is_hotspot_module'] * 15 +
            risk_components['bug_density'] * 10
        )
        risk_score = min(100, risk_score)
        
        return float(failure_prob), float(risk_score)
    
    def _preprocess_commit(self, commit_df):
        """Add engineered features to commit data"""
        
        # Basic feature count
        commit_df['num_modules'] = commit_df['modules_affected'].str.split(',').str.len()
        
        # Critical modules check
        critical_modules = ['AHB_Controller', 'Memory_Controller', 'Cache_L1', 'Interconnect']
        commit_df['has_critical_module'] = commit_df['modules_affected'].apply(
            lambda x: 1 if any(mod in x for mod in critical_modules) else 0
        )
        
        # Engineered features
        commit_df['code_churn_normalized'] = commit_df['code_churn_ratio'] * commit_df['files_modified']
        commit_df['bug_density'] = commit_df['historical_bug_frequency'] / (commit_df['modules_affected_count'] + 1)
        
        # Risk score
        commit_df['risk_score'] = (
            (1 - commit_df['author_experience_years'] / 20) * 0.2 +
            commit_df['code_churn_ratio'] * 0.3 +
            commit_df['is_hotspot_module'] * 0.2 +
            (commit_df['bug_density'] / (commit_df['bug_density'].max() + 1)) * 0.3
        )
        
        return commit_df
    
    def process_commits(self, commits_df):
        """
        Process a batch of commits and generate optimized test queue
        
        Args:
            commits_df: DataFrame with multiple commits
            
        Returns:
            optimized_df: DataFrame with predictions and priority rankings
        """
        
        print(f"\n[Processing {len(commits_df)} commits...]")
        
        results = []
        
        for idx, row in commits_df.iterrows():
            commit_record = commits_df.iloc[[idx]]
            failure_prob, risk_score = self.predict_failure_probability(commit_record)
            
            results.append({
                'commit_id': row['commit_id'],
                'author_id': row['author_id'],
                'commit_date': row['commit_date'],
                'modules_affected': row['modules_affected'],
                'files_modified': row['files_modified'],
                'code_churn_ratio': row['code_churn_ratio'],
                'historical_bug_frequency': row['historical_bug_frequency'],
                'regression_time_hours': row['regression_time_hours'],
                'predicted_failure_probability': failure_prob,
                'risk_score': risk_score,
                'ground_truth_failed': row['test_failed'] if 'test_failed' in row.index else None
            })
        
        optimized_df = pd.DataFrame(results)
        
        # Sort by risk score (descending) - highest risk tests first
        optimized_df = optimized_df.sort_values('risk_score', ascending=False).reset_index(drop=True)
        
        # Add priority ranking
        optimized_df['test_priority'] = range(1, len(optimized_df) + 1)
        
        # Reorder columns
        optimized_df = optimized_df[[
            'test_priority', 'commit_id', 'risk_score', 'predicted_failure_probability',
            'modules_affected', 'code_churn_ratio', 'historical_bug_frequency',
            'files_modified', 'regression_time_hours', 'ground_truth_failed'
        ]]
        
        return optimized_df
    
    def calculate_optimization_impact(self, optimized_df, original_regression_time=24):
        """
        Calculate ROI/impact of test reordering
        Assumes running tests sequentially and stopping after first N failures caught
        """
        
        print(f"\n[Calculating Optimization Impact]")
        
        # Assume we catch 80% of issues by running top 30% of tests
        total_tests = len(optimized_df)
        tests_to_run_early = max(1, int(total_tests * 0.3))
        
        # Estimate time savings
        avg_test_time = original_regression_time / total_tests
        early_stop_time = tests_to_run_early * avg_test_time
        time_saved_percent = (1 - early_stop_time / original_regression_time) * 100
        
        # Calculate failure detection efficiency
        top_tests = optimized_df.head(tests_to_run_early)
        if 'ground_truth_failed' in optimized_df.columns:
            actual_failures_in_top = top_tests['ground_truth_failed'].sum()
            total_failures = optimized_df['ground_truth_failed'].sum()
            if total_failures > 0:
                failure_catch_rate = (actual_failures_in_top / total_failures) * 100
            else:
                failure_catch_rate = 0
        else:
            failure_catch_rate = None
        
        # Cost estimation (assuming AWS compute at $0.50/hour)
        cost_per_hour = 0.50
        original_cost = original_regression_time * cost_per_hour
        optimized_cost = early_stop_time * cost_per_hour
        cost_saved = original_cost - optimized_cost
        
        impact = {
            'total_tests': total_tests,
            'tests_run_in_optimized_mode': tests_to_run_early,
            'original_regression_hours': original_regression_time,
            'optimized_regression_hours': round(early_stop_time, 2),
            'time_saved_hours': round(original_regression_time - early_stop_time, 2),
            'time_saved_percent': round(time_saved_percent, 2),
            'original_cost_usd': round(original_cost, 2),
            'optimized_cost_usd': round(optimized_cost, 2),
            'cost_saved_usd': round(cost_saved, 2),
            'cost_saved_percent': round((cost_saved / original_cost) * 100, 2),
            'failure_catch_rate_percent': round(failure_catch_rate, 2) if failure_catch_rate else None,
        }
        
        return impact
    
    def generate_report(self, optimized_df, impact_metrics):
        """Generate human-readable optimization report"""
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        RTL VERIFICATION TEST QUEUE OPTIMIZATION REPORT                       ║
║                         AI-DRIVEN PRIORITIZATION                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

📊 OPTIMIZATION SUMMARY
───────────────────────────────────────────────────────────────────────────────
Total Commits Analyzed:           {impact_metrics['total_tests']}
Tests to Run (First Pass):        {impact_metrics['tests_run_in_optimized_mode']} (30% of queue)

⏱️  TIME IMPACT
───────────────────────────────────────────────────────────────────────────────
Original Regression Time:         {impact_metrics['original_regression_hours']:.2f} hours
Optimized Regression Time:        {impact_metrics['optimized_regression_hours']:.2f} hours
Time Saved:                       {impact_metrics['time_saved_hours']:.2f} hours ({impact_metrics['time_saved_percent']:.1f}%)

💰 COST IMPACT (AWS Compute @ $0.50/hour)
───────────────────────────────────────────────────────────────────────────────
Original Cost:                    ${impact_metrics['original_cost_usd']:.2f}
Optimized Cost:                   ${impact_metrics['optimized_cost_usd']:.2f}
Cost Saved:                       ${impact_metrics['cost_saved_usd']:.2f} ({impact_metrics['cost_saved_percent']:.1f}%)

📈 ANNUALIZED IMPACT (250 commits/year per developer × 20 developers)
───────────────────────────────────────────────────────────────────────────────
Annual Commits:                   {250 * 20:,}
Annual Time Saved:                {(impact_metrics['time_saved_hours'] * 250 * 20):,.0f} hours/year
Annual Cost Saved:                ${(impact_metrics['cost_saved_usd'] * 250 * 20):,.0f}/year

🎯 FAILURE DETECTION QUALITY
───────────────────────────────────────────────────────────────────────────────
Failures Caught in First 30%:     {impact_metrics['failure_catch_rate_percent']}% of total failures detected

📋 TOP 10 HIGH-RISK TESTS (Test Priority 1-10)
───────────────────────────────────────────────────────────────────────────────
"""
        
        top_10 = optimized_df.head(10)
        for _, test in top_10.iterrows():
            report += f"""
Priority {test['test_priority']:2d}: {test['commit_id']}
  ├─ Risk Score:                {test['risk_score']:.1f}/100
  ├─ Failure Probability:       {test['predicted_failure_probability']*100:.1f}%
  ├─ Modules Affected:          {test['modules_affected']}
  └─ Expected Runtime:          {test['regression_time_hours']:.2f} hours
"""
        
        report += f"""
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        
        return report


def main():
    print("\n" + "="*80)
    print("CI/CD TEST QUEUE OPTIMIZER - RTL Verification System")
    print("="*80)
    
    # Initialize optimizer
    optimizer = TestQueueOptimizer()
    
    # Load recent commits
    print("\n[Loading recent commits for processing...]")
    recent_commits = pd.read_csv('data/recent_commits.csv')
    print(f"✓ Loaded {len(recent_commits)} recent commits")
    
    # Process commits
    optimized_queue = optimizer.process_commits(recent_commits)
    
    # Calculate impact
    impact = optimizer.calculate_optimization_impact(optimized_queue)
    
    # Generate and print report
    report = optimizer.generate_report(optimized_queue, impact)
    print(report)
    
    # Save optimized queue
    try:
        optimized_queue.to_csv('data/optimized_test_queue.csv', index=False)
        print(f"\n✓ Optimized test queue saved to: data/optimized_test_queue.csv")
    except PermissionError as e:
        temp_path = 'data/optimized_test_queue_temp.csv'
        optimized_queue.to_csv(temp_path, index=False)
        print(f"⚠️  PermissionError writing optimized queue: {e}")
        print(f"   — wrote to {temp_path} instead; close any program locking the original file and rename it when possible.")

    # Save impact metrics
    try:
        with open('data/optimization_impact.json', 'w') as f:
            json.dump(impact, f, indent=2)
        print(f"✓ Impact metrics saved to: data/optimization_impact.json")
    except PermissionError as e:
        temp_path = 'data/optimization_impact_temp.json'
        with open(temp_path, 'w') as f:
            json.dump(impact, f, indent=2)
        print(f"⚠️  PermissionError writing impact metrics: {e}")
        print(f"   — wrote to {temp_path} instead; close any program locking the original file and rename it when possible.")
    
    print("\n" + "="*80)
    print("✅ Test queue optimization completed successfully!")
    print("="*80)


if __name__ == '__main__':
    main()
