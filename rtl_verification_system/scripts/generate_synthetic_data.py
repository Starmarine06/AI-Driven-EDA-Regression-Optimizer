"""
Synthetic RTL Verification Dataset Generator
Generates realistic mock data for RTL commit and verification history (5000+ records)
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

def generate_synthetic_data(num_commits=5000):
    """
    Generate synthetic RTL verification dataset
    
    Features:
    - commit_id: Unique identifier
    - author_id: Developer identifier (1-50 developers)
    - author_experience: Years of experience (0-20 years)
    - commit_date: Date of commit
    - files_modified: Number of files changed (1-50)
    - lines_added: Lines of code added (10-5000)
    - lines_deleted: Lines of code deleted (0-3000)
    - modules_affected: Number of RTL modules touched (1-15)
    - module_names: List of affected modules
    - code_churn_ratio: (added + deleted) / (added + deleted + existing)
    - is_hotspot_module: Touching critical modules (AHB, memory, cache)
    - historical_bug_frequency: Historical bugs in affected modules (0-10 per module)
    - is_test_failed: Target variable - did any test fail? (0/1)
    - test_fail_count: Number of tests that failed
    - regression_time_hours: Time to run regression suite
    """
    
    # Define RTL modules and their complexity
    rtl_modules = {
        'AHB_Controller': 9,      # High complexity
        'Memory_Controller': 9,
        'Cache_L1': 8,
        'Cache_L2': 8,
        'ALU': 7,
        'Register_File': 6,
        'Data_Path': 8,
        'Control_Unit': 8,
        'Interconnect': 9,
        'I2C_Interface': 5,
        'SPI_Interface': 5,
        'UART_Controller': 4,
        'GPIO_Controller': 3,
        'Clock_Domain': 7,
        'Reset_Logic': 4,
    }
    
    authors = [f'author_{i}' for i in range(1, 51)]
    base_date = datetime(2024, 1, 1)
    
    data = []
    
    for commit_idx in range(num_commits):
        # Author info
        author_id = random.choice(authors)
        author_experience = np.random.normal(8, 5, 1)[0]  # Mean 8 years, std 5
        author_experience = max(0, min(20, author_experience))  # Clamp 0-20
        
        # Commit metadata
        commit_date = base_date + timedelta(hours=random.randint(0, 24*365))
        files_modified = np.random.randint(1, 51)
        lines_added = np.random.randint(10, 5001)
        lines_deleted = np.random.randint(0, 3001)
        
        # Modules affected
        num_modules = np.random.randint(1, 16)
        affected_modules = random.sample(list(rtl_modules.keys()), num_modules)
        module_names = ','.join(affected_modules)
        
        # Calculate code churn ratio
        total_churn = lines_added + lines_deleted
        code_churn_ratio = total_churn / (total_churn + 5000) if total_churn > 0 else 0
        
        # Hotspot check (critical modules)
        hotspot_modules = ['AHB_Controller', 'Memory_Controller', 'Interconnect']
        is_hotspot = 1 if any(mod in affected_modules for mod in hotspot_modules) else 0
        
        # Historical bug frequency per module (increases with complexity)
        historical_bug_freq = 0
        for module in affected_modules:
            complexity = rtl_modules[module]
            # Bugs correlate with complexity and random history
            bugs_in_module = np.random.poisson(complexity / 2) 
            historical_bug_freq += bugs_in_module
        
        # Regression time (increases with modules and churn)
        base_regression_time = 4
        regression_time_hours = base_regression_time + (num_modules * 0.5) + (code_churn_ratio * 10)
        regression_time_hours = max(2, regression_time_hours)
        
        # Predict failure: likelihood increases with complexity, churn, and bugs
        failure_probability = (
            0.05 +  # Base failure rate
            (is_hotspot * 0.15) +  # Hotspot penalty
            (historical_bug_freq * 0.03) +  # Bug history
            (code_churn_ratio * 0.2) +  # Code churn
            (1 - author_experience / 20) * 0.1  # Author inexperience
        )
        
        # Add randomness
        failure_probability += np.random.normal(0, 0.05)
        failure_probability = max(0, min(1, failure_probability))
        
        # Determine if test failed (stochastic based on probability)
        is_test_failed = 1 if random.random() < failure_probability else 0
        
        # Number of failed tests (if any)
        if is_test_failed:
            test_fail_count = np.random.randint(1, 8)
        else:
            test_fail_count = 0
        
        data.append({
            'commit_id': f'commit_{commit_idx:06d}',
            'author_id': author_id,
            'author_experience_years': round(author_experience, 2),
            'commit_date': commit_date.strftime('%Y-%m-%d %H:%M:%S'),
            'files_modified': files_modified,
            'lines_added': lines_added,
            'lines_deleted': lines_deleted,
            'modules_affected_count': num_modules,
            'modules_affected': module_names,
            'code_churn_ratio': round(code_churn_ratio, 4),
            'is_hotspot_module': is_hotspot,
            'historical_bug_frequency': historical_bug_freq,
            'regression_time_hours': round(regression_time_hours, 2),
            'failure_probability_true': round(failure_probability, 4),
            'test_failed': is_test_failed,
            'test_fail_count': test_fail_count,
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    return df


def generate_recent_commits(num_recent=100):
    """
    Generate 'recent' commits (last 7 days) for testing the system
    """
    
    rtl_modules = {
        'AHB_Controller': 9,
        'Memory_Controller': 9,
        'Cache_L1': 8,
        'Cache_L2': 8,
        'ALU': 7,
        'Register_File': 6,
        'Data_Path': 8,
        'Control_Unit': 8,
        'Interconnect': 9,
        'I2C_Interface': 5,
        'SPI_Interface': 5,
        'UART_Controller': 4,
        'GPIO_Controller': 3,
        'Clock_Domain': 7,
        'Reset_Logic': 4,
    }
    
    authors = [f'author_{i}' for i in range(1, 51)]
    base_date = datetime.now() - timedelta(days=7)
    
    data = []
    
    for commit_idx in range(num_recent):
        author_id = random.choice(authors)
        author_experience = np.random.normal(8, 5, 1)[0]
        author_experience = max(0, min(20, author_experience))
        
        commit_date = base_date + timedelta(hours=random.randint(0, 7*24))
        files_modified = np.random.randint(1, 51)
        lines_added = np.random.randint(10, 5001)
        lines_deleted = np.random.randint(0, 3001)
        
        num_modules = np.random.randint(1, 16)
        affected_modules = random.sample(list(rtl_modules.keys()), num_modules)
        module_names = ','.join(affected_modules)
        
        total_churn = lines_added + lines_deleted
        code_churn_ratio = total_churn / (total_churn + 5000) if total_churn > 0 else 0
        
        hotspot_modules = ['AHB_Controller', 'Memory_Controller', 'Interconnect']
        is_hotspot = 1 if any(mod in affected_modules for mod in hotspot_modules) else 0
        
        historical_bug_freq = 0
        for module in affected_modules:
            complexity = rtl_modules[module]
            bugs_in_module = np.random.poisson(complexity / 2)
            historical_bug_freq += bugs_in_module
        
        base_regression_time = 4
        regression_time_hours = base_regression_time + (num_modules * 0.5) + (code_churn_ratio * 10)
        regression_time_hours = max(2, regression_time_hours)
        
        failure_probability = (
            0.05 +
            (is_hotspot * 0.15) +
            (historical_bug_freq * 0.03) +
            (code_churn_ratio * 0.2) +
            (1 - author_experience / 20) * 0.1
        )
        
        failure_probability += np.random.normal(0, 0.05)
        failure_probability = max(0, min(1, failure_probability))
        
        is_test_failed = 1 if random.random() < failure_probability else 0
        test_fail_count = np.random.randint(1, 8) if is_test_failed else 0
        
        data.append({
            'commit_id': f'recent_commit_{commit_idx:04d}',
            'author_id': author_id,
            'author_experience_years': round(author_experience, 2),
            'commit_date': commit_date.strftime('%Y-%m-%d %H:%M:%S'),
            'files_modified': files_modified,
            'lines_added': lines_added,
            'lines_deleted': lines_deleted,
            'modules_affected_count': num_modules,
            'modules_affected': module_names,
            'code_churn_ratio': round(code_churn_ratio, 4),
            'is_hotspot_module': is_hotspot,
            'historical_bug_frequency': historical_bug_freq,
            'regression_time_hours': round(regression_time_hours, 2),
            'failure_probability_true': round(failure_probability, 4),
            'test_failed': is_test_failed,
            'test_fail_count': test_fail_count,
        })
    
    df = pd.DataFrame(data)
    return df


def main():
    print("Generating synthetic RTL verification dataset...")
    
    # Generate historical data
    df_historical = generate_synthetic_data(num_commits=5000)
    try:
        df_historical.to_csv('data/rtl_verification_history.csv', index=False)
        print(f"✓ Generated {len(df_historical)} historical commits")
        print(f"  - Failure rate: {df_historical['test_failed'].mean()*100:.2f}%")
        print(f"  - Average modules per commit: {df_historical['modules_affected_count'].mean():.2f}")
        print(f"  - Average regression time: {df_historical['regression_time_hours'].mean():.2f} hours")
    except PermissionError as e:
        temp_path = 'data/rtl_verification_history_temp.csv'
        df_historical.to_csv(temp_path, index=False)
        print(f"⚠️  PermissionError writing history file: {e}")
        print(f"   — wrote dataset to {temp_path} instead; please close any programs locking the original file and move/rename {temp_path} when ready.")
    
    # Generate recent commits for testing
    df_recent = generate_recent_commits(num_recent=100)
    try:
        df_recent.to_csv('data/recent_commits.csv', index=False)
        print(f"\n✓ Generated {len(df_recent)} recent test commits")
    except PermissionError as e:
        temp_path = 'data/recent_commits_temp.csv'
        df_recent.to_csv(temp_path, index=False)
        print(f"⚠️  PermissionError writing recent commits file: {e}")
        print(f"   — wrote dataset to {temp_path} instead; please close any programs locking the original file and move/rename {temp_path} when ready.")
    
    # Display sample data
    print("\n📊 Sample of historical data (first 5 rows):")
    print(df_historical.head(5).to_string())
    
    print("\n📊 Data statistics:")
    print(df_historical[['files_modified', 'lines_added', 'lines_deleted', 
                         'modules_affected_count', 'code_churn_ratio', 
                         'historical_bug_frequency', 'regression_time_hours']].describe())


if __name__ == '__main__':
    main()
