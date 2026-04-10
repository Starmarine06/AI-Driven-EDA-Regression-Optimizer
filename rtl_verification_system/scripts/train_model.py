"""
ML Model Training Pipeline for RTL Failure Prediction
Trains XGBoost model on synthetic RTL verification dataset
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
    roc_curve, precision_recall_curve, f1_score
)
import xgboost as xgb
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json
from datetime import datetime

def preprocess_data(df):
    """
    Preprocess RTL dataset for ML training
    """
    df = df.copy()
    
    # Create additional features from module list
    df['num_modules'] = df['modules_affected'].str.split(',').str.len()
    
    # Key modules (more likely to have bugs)
    critical_modules = ['AHB_Controller', 'Memory_Controller', 'Cache_L1', 'Interconnect']
    df['has_critical_module'] = df['modules_affected'].apply(
        lambda x: 1 if any(mod in x for mod in critical_modules) else 0
    )
    
    # Features for ML
    feature_cols = [
        'author_experience_years',
        'files_modified',
        'lines_added',
        'lines_deleted',
        'modules_affected_count',
        'code_churn_ratio',
        'is_hotspot_module',
        'historical_bug_frequency',
        'regression_time_hours',
        'has_critical_module'
    ]
    
    # Create additional engineered features
    df['code_churn_normalized'] = df['code_churn_ratio'] * df['files_modified']
    df['bug_density'] = df['historical_bug_frequency'] / (df['modules_affected_count'] + 1)
    df['risk_score'] = (
        (1 - df['author_experience_years'] / 20) * 0.2 +
        df['code_churn_ratio'] * 0.3 +
        df['is_hotspot_module'] * 0.2 +
        (df['bug_density'] / (df['bug_density'].max() + 1)) * 0.3
    )
    
    feature_cols.extend(['code_churn_normalized', 'bug_density', 'risk_score'])
    
    X = df[feature_cols]
    y = df['test_failed']
    
    return X, y, feature_cols


def train_model(data_path='data/rtl_verification_history.csv', 
                model_save_path='models/rtl_predictor_model.pkl'):
    """
    Train XGBoost model for RTL failure prediction
    """
    
    print("=" * 80)
    print("RTL Verification Failure Prediction - Model Training Pipeline")
    print("=" * 80)
    
    # Load data
    print("\n[1/6] Loading RTL verification history...")
    df = pd.read_csv(data_path)
    print(f"✓ Loaded {len(df)} records")
    print(f"  Total features available: {len(df.columns)}")
    
    # Preprocess
    print("\n[2/6] Preprocessing data and engineering features...")
    X, y, feature_cols = preprocess_data(df)
    print(f"✓ Created {len(feature_cols)} features:")
    for i, col in enumerate(feature_cols, 1):
        print(f"  {i:2d}. {col}")
    
    print(f"\n  Target distribution:")
    print(f"    - Test Passed: {(y == 0).sum()} ({(y == 0).sum()/len(y)*100:.2f}%)")
    print(f"    - Test Failed: {(y == 1).sum()} ({(y == 1).sum()/len(y)*100:.2f}%)")
    
    # Train-test split
    print("\n[3/6] Splitting data (80% train, 20% test)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"✓ Training set: {len(X_train)} samples")
    print(f"✓ Test set: {len(X_test)} samples")
    
    # Scale features
    print("\n[4/6] Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    print("✓ Features scaled using StandardScaler")
    
    # Train XGBoost model
    print("\n[5/6] Training XGBoost model...")
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='logloss',
        use_label_encoder=False
    )
    
    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        verbose=False
    )
    print("✓ Model training completed")
    
    # Evaluate model
    print("\n[6/6] Evaluating model performance...")
    
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    # Metrics
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    
    print(f"\n📊 Model Performance Metrics:")
    print(f"  - ROC-AUC Score: {roc_auc:.4f}")
    print(f"  - F1 Score: {f1:.4f}")
    print(f"\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Passed', 'Failed']))
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    print(f"Confusion Matrix:")
    print(f"  True Negatives:  {cm[0, 0]:6d}  |  False Positives: {cm[0, 1]:6d}")
    print(f"  False Negatives: {cm[1, 0]:6d}  |  True Positives:  {cm[1, 1]:6d}")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(f"\n🎯 Top 10 Most Important Features:")
    for idx, row in feature_importance.head(10).iterrows():
        print(f"  {row['feature']:30s} : {row['importance']:.4f}")
    
    # Save model and scaler
    print(f"\n💾 Saving model and artifacts...")
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    
    joblib.dump(model, model_save_path)
    joblib.dump(scaler, 'models/scaler.pkl')
    joblib.dump(feature_cols, 'models/feature_cols.pkl')
    
    # Save metadata
    metadata = {
        'timestamp': datetime.now().isoformat(),
        'training_samples': len(X_train),
        'test_samples': len(X_test),
        'roc_auc_score': float(roc_auc),
        'f1_score': float(f1),
        'model_type': 'XGBClassifier',
        'n_estimators': 100,
        'max_depth': 6,
        'feature_cols': feature_cols,
        'feature_importance': feature_importance.to_dict('records')
    }
    
    with open('models/model_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✓ Model saved to: {model_save_path}")
    print(f"✓ Scaler saved to: models/scaler.pkl")
    print(f"✓ Feature columns saved to: models/feature_cols.pkl")
    print(f"✓ Metadata saved to: models/model_metadata.json")
    
    print("\n" + "=" * 80)
    print("✅ Model training pipeline completed successfully!")
    print("=" * 80)
    
    return model, scaler, feature_cols, metadata


if __name__ == '__main__':
    train_model()
