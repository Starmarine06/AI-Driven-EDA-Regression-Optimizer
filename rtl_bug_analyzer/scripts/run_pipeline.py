"""
Main Pipeline - Orchestrates log analysis and bug triage
"""

import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from log_parser import LogParser
from bug_classifier import BugClassifier


def main():
    print("\n" + "="*80)
    print("RTL BUG ANALYZER - Log Analysis & Triage System")
    print("="*80)
    
    # Initialize components
    parser = LogParser()
    classifier = BugClassifier()
    
    # Check for log files
    log_dir = Path('../data')
    log_files = list(log_dir.glob('*.log')) if log_dir.exists() else []
    
    if not log_files:
        print("\n⚠️  No log files found in data/ directory")
        print("   Generating synthetic test logs...")
        generate_synthetic_logs()
        log_files = list(log_dir.glob('*.log'))
    
    print(f"\n📋 Found {len(log_files)} log file(s) to analyze\n")
    
    # Parse all logs
    all_logs = []
    for log_file in log_files:
        print(f"[1/3] Parsing: {log_file.name}")
        logs_df = parser.parse_log_file(str(log_file))
        if not logs_df.empty:
            all_logs.append(logs_df)
    
    if not all_logs:
        print("\n❌ No logs to analyze")
        return
    
    # Combine logs
    combined_logs = pd.concat(all_logs, ignore_index=True)
    print(f"\n✓ Loaded {len(combined_logs)} failure entries\n")
    
    # Extract unique signatures
    print("[2/3] Extracting unique failure signatures...")
    signatures = parser.extract_unique_signatures(combined_logs)
    print(f"✓ Found {len(signatures)} unique failure signatures\n")
    
    # Classify bugs and assign priority
    print("[3/3] Classifying bugs and assigning priorities...")
    bugs = classifier.classify_bugs(signatures)
    print(f"✓ Classified {len(bugs)} bugs\n")
    
    # Show categorized summary and recent changes info
    summary = summarize_signatures(signatures)
    changes = get_recent_changes(signatures)

    # Display results
    display_results(bugs, summary, changes)
    
    # Save results
    bugs.to_csv('../data/bug_triage_list.csv', index=False)
    
    print(f"\n✓ Results saved to data/bug_triage_list.csv\n")


def display_results(bugs_df: pd.DataFrame, summary: dict, changes: dict):
    """Display analysis results and top bug to work on"""
    
    print("\n" + "="*80)
    print("BUG TRIAGE SUMMARY")
    print("="*80)
    
    # show categorized summary
    print(f"\n📁 Error categories:")
    for category, count in summary['by_category'].items():
        print(f"  - {category}: {count} signatures")
    print(f"\n📦 Failures per module:")
    for module, count in summary['by_module'].items():
        print(f"  - {module}: {count}")
    print(f"\n📊 Total Bugs Found: {len(bugs_df)}\n")
    
    # display recent changes if any
    print("🔧 Recent design/testbench changes:")
    if changes:
        for module, commits in changes.items():
            if commits:
                print(f"  * {module}: {commits}")
    else:
        print("  (no git history found or no relevant commits)")
    
    # Display prioritized bug list
    print("="*80)
    print("ALL IDENTIFIED BUGS (Ranked by Priority)")
    print("="*80 + "\n")
    
    suggestions = {
        'assertion_failure': 'Check assertion statements and UVM legality.',
        'data_corruption': 'Verify memory write/read paths and checksum logic.',
        'deadlock': 'Inspect arbiter and handshake logic for stalls.',
        'timeout': 'Look into clock/reset domains and testbench timeouts.',
        'illegal_state': 'Trace FSM transitions for invalid states.',
        'clock_issue': 'Review clock domain crossings and constraints.',
        'reset_issue': 'Ensure resets propagate to all registers.',
        'interface_error': 'Check protocol compliance on interfaces.',
        'memory_error': 'Validate address decoding and memory models.',
        'cache_error': 'Analyze cache coherency operations.',
        'arbitration': 'Inspect request/grant arbitration logic.',
        'coverage': 'Look at missed coverage points in UVM reports.',
        'unknown': 'Examine log message for additional clues.'
    }
    
    for idx, (_, bug) in enumerate(bugs_df.iterrows(), 1):
        priority_emoji = '🔴' if bug['priority_score'] > 10 else '🟠' if bug['priority_score'] > 4 else '🟡'
        
        print(f"{idx}. {priority_emoji} PRIORITY SCORE: {bug['priority_score']}")
        print(f"   Failure Type: {bug['failure_type']} ({bug.get('category','')})")
        print(f"   Module: {bug['module']}")
        print(f"   Recurrence Count: {bug['recurrence_count']}")
        print(f"   Testcase Impact: {bug['testcase_impact']} test(s) affected")
        print(f"   Total Failures: {bug['total_failures']}")
        print(f"   Impact Level: {bug['impact_level']}")
        if bug['failure_type'] in suggestions:
            print(f"   🔍 Debug hint: {suggestions[bug['failure_type']]}\n")
        else:
            print()
    
    # Highlight top bug to work on
    print("="*80)
    print("🎯 TOP BUG TO WORK ON")
    print("="*80 + "\n")
    
    top_bug = bugs_df.iloc[0]
    print(f"Priority Score: {top_bug['priority_score']}")
    print(f"Failure Type: {top_bug['failure_type']}")
    print(f"Module: {top_bug['module']}")
    print(f"Recurrence Count: {top_bug['recurrence_count']} occurrences")
    print(f"Testcase Impact: {top_bug['testcase_impact']} unique test case(s) affected")
    print(f"Total Failures: {top_bug['total_failures']} total failure instances")
    print(f"Severity: {top_bug['severity']}")
    print(f"\nFormula: Priority Score = Recurrence Count × Testcase Impact")
    print(f"         Priority Score = {top_bug['recurrence_count']} × {top_bug['testcase_impact']} = {top_bug['priority_score']}\n")


def summarize_signatures(signatures: pd.DataFrame) -> dict:
    """Return summary counts by category and module"""
    summary = {
        'by_category': signatures['category'].value_counts().to_dict() if 'category' in signatures else {},
        'by_module': signatures['module'].value_counts().to_dict()
    }
    return summary


def get_recent_changes(signatures: pd.DataFrame) -> dict:
    """Look for recent git commits mentioning each module"""
    changes = {}
    try:
        import subprocess
        modules = signatures['module'].unique()
        for module in modules:
            # naive git grep in commit messages
            cmd = ["git", "log", "-n", "3", "--pretty=format:%h:%s", "--grep", module]
            result = subprocess.run(cmd, capture_output=True, text=True)
            changes[module] = result.stdout.strip().replace('\n', ' | ')
    except Exception:
        return {}
    return changes


def generate_synthetic_logs():

    """Generate synthetic test logs for demonstration"""
    
    log_dir = Path('../data')
    log_dir.mkdir(exist_ok=True)
    
    # Format: [TIMESTAMP] [MODULE] TEST=testcase_id FAILURES=count ERROR: Message
    failure_patterns = [
        ("2026-03-06 15:30:45 [AHB_Controller] TEST=test_ahb_001 FAILURES=5 ERROR: Assertion failure in handshake protocol", "CRITICAL"),
        ("2026-03-06 15:30:46 [AHB_Controller] TEST=test_ahb_002 FAILURES=5 ERROR: Assertion failure in handshake protocol", "CRITICAL"),
        ("2026-03-06 15:30:47 [AHB_Controller] TEST=test_ahb_003 FAILURES=5 ERROR: Assertion failure in handshake protocol", "CRITICAL"),
        ("2026-03-06 15:31:12 [Memory_Controller] TEST=test_mem_001 FAILURES=8 FATAL: Data corruption detected in cache write", "CRITICAL"),
        ("2026-03-06 15:31:13 [Memory_Controller] TEST=test_mem_002 FAILURES=8 FATAL: Data corruption detected in cache write", "CRITICAL"),
        ("2026-03-06 15:32:00 [Interconnect] TEST=test_interconnect_001 FAILURES=3 ERROR: Arbitration deadlock on port 3", "HIGH"),
        ("2026-03-06 15:33:15 [Cache_L1] TEST=test_cache_001 FAILURES=4 ERROR: Cache coherency violation", "HIGH"),
        ("2026-03-06 15:34:30 [ALU] TEST=test_alu_001 FAILURES=2 WARNING: Illegal state machine transition", "MEDIUM"),
        ("2026-03-06 15:35:45 [Control_Unit] TEST=test_ctrl_001 FAILURES=3 ERROR: Reset signal timeout", "HIGH"),
        ("2026-03-06 15:36:20 [Clock_Domain] TEST=test_clk_001 FAILURES=6 FATAL: Clock domain crossing violation", "CRITICAL"),
        ("2026-03-06 15:37:00 [Data_Path] TEST=test_dp_001 FAILURES=2 ERROR: Invalid operation detected", "MEDIUM"),
        ("2026-03-06 15:38:10 [Reset_Logic] TEST=test_rst_001 FAILURES=1 WARNING: Incomplete reset sequence", "MEDIUM"),
        ("2026-03-06 15:39:25 [Register_File] TEST=test_rf_001 FAILURES=4 ERROR: Data mismatch in read operation", "HIGH"),
    ]
    
    # Create synthetic log file
    log_file = log_dir / 'verification_run_001.log'
    with open(log_file, 'w') as f:
        for message, _ in failure_patterns:
            f.write(message + '\n')
    
    print(f"✓ Generated synthetic log: {log_file}\n")


if __name__ == '__main__':
    main()
