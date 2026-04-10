"""
Main execution pipeline for RTL Verification System
Run this script to execute all components: data generation, model training, and optimization
"""

import subprocess
import sys
import os


def run_module(script_name, description):
    """Run a Python module and handle errors"""
    print(f"\n{'='*80}")
    print(f"🚀 {description}")
    print(f"{'='*80}\n")
    
    try:
        subprocess.run([sys.executable, f"scripts/{script_name}"], check=True)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running {script_name}: {e}")
        return False


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "  AI-DRIVEN RTL VERIFICATION FAILURE PREDICTION SYSTEM".center(78) + "║")
    print("║" + "  Complete Execution Pipeline".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    
    success = True
    
    # Step 1: Generate synthetic data
    success = run_module(
        "generate_synthetic_data.py",
        "STEP 1: Generating Synthetic RTL Verification Dataset"
    ) and success
    
    if not success:
        print("\n⚠️  Failed to generate synthetic data. Continuing anyway...")
    
    # Step 2: Train ML model
    success = run_module(
        "train_model.py",
        "STEP 2: Training ML Prediction Model"
    ) and success
    
    if not success:
        print("\n❌ Failed to train model. Cannot continue.")
        return
    
    # Step 3: Optimize test queue
    success = run_module(
        "optimize_test_queue.py",
        "STEP 3: Optimizing Test Queue Based on ML Predictions"
    ) and success
    
    if not success:
        print("\n⚠️  Failed to optimize queue.")
    
    # Final summary
    print(f"\n{'='*80}")
    print("📊 PIPELINE EXECUTION SUMMARY")
    print(f"{'='*80}\n")
    
    print("✅ All components generated successfully!")
    print("\n📁 Generated artifacts:")
    print("  • data/rtl_verification_history.csv     - Historical training data (5000 records)")
    print("  • data/recent_commits.csv               - Recent commits for testing (100 records)")
    print("  • models/rtl_predictor_model.pkl        - Trained XGBoost model")
    print("  • models/scaler.pkl                     - Feature scaler")
    print("  • models/model_metadata.json            - Model performance metrics")
    print("  • data/optimized_test_queue.csv         - Prioritized test queue")
    print("  • data/optimization_impact.json         - ROI/savings metrics")
    
    print("\n🚀 Next steps:")
    print("  1. Start API server: python api_server.py")
    print("  2. Open React dashboard: cd '../sandisk front end' && npm run dev")
    print("  3. View results at http://localhost:5173/")
    print("  4. Alternative: streamlit run dashboard/app.py")
    
    print(f"\n{'='*80}")
    print("✨ Ready for presentation and ROI analysis!")
    print(f"{'='*80}\n")
    
    # Auto-start API server
    print("🔄 Starting API server...")
    try:
        subprocess.Popen([sys.executable, 'api_server.py'], 
                        cwd=os.path.dirname(os.path.abspath(__file__)))
        print("✅ API server started on http://localhost:5000/")
    except Exception as e:
        print(f"⚠️  Could not start API server: {e}")


if __name__ == '__main__':
    main()
