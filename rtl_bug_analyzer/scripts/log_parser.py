"""
RTL Log Parser - Extracts failure information from verification logs
"""

import re
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple


class LogParser:
    """Parse RTL verification logs and extract failure signatures"""
    
    def __init__(self):
        # Common RTL failure patterns
        self.failure_patterns = {
            'assertion_failure': r'Assertion\s+failure|ASSERTION.*FAIL',
            'timeout': r'Timeout|Time\s+out|exceeded|TIMEOUT',
            'illegal_state': r'Illegal\s+state|Invalid\s+state|BAD.*STATE',
            'deadlock': r'[Dd]eadlock|No\s+progress|Stalled',
            'data_corruption': r'Data\s+mismatch|Corruption|Expected.*Got',
            'clock_issue': r'Clock|CLK.*fail|Clock\s+domain',
            'reset_issue': r'Reset\s+fail|RST.*ERROR|reset\s+error',
            'interface_error': r'Interface|Protocol\s+error|Handshake\s+fail',
            'memory_error': r'Memory|SRAM|RAM.*fail|Address.*error',
            'cache_error': r'Cache|Coherency|Cache.*miss',
            'arbitration': r'Arbit|Grant|Request.*fail',
            'coverage': r'Coverage|Coverage.*fail|CovPoint',
        }
    
    def parse_log_file(self, log_path: str) -> pd.DataFrame:
        """Parse a single log file and extract failures"""
        
        logs = []
        
        try:
            with open(log_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            print(f"❌ Error reading {log_path}: {e}")
            return pd.DataFrame()
        
        # Parse each line
        for idx, line in enumerate(lines):
            if self._is_failure_line(line):
                log_entry = {
                    'line_number': idx,
                    'timestamp': self._extract_timestamp(line),
                    'module': self._extract_module(line),
                    'failure_type': self._classify_failure(line),
                    'category': self._extract_category(line),
                    'message': line.strip(),
                    'severity': self._assess_severity(line),
                    'testcase': self._extract_testcase(line),
                    'failure_count': self._extract_failure_count(line),
                }
                logs.append(log_entry)
        
        return pd.DataFrame(logs)
    
    def _is_failure_line(self, line: str) -> bool:
        """Check if line contains a failure indicator"""
        failure_keywords = ['ERROR', 'FAIL', 'FATAL', 'ASSERT', 'Exception', 
                           'Timeout', 'Deadlock', 'Illegal', 'Mismatch']
        return any(keyword in line for keyword in failure_keywords)
    
    def _extract_timestamp(self, line: str) -> str:
        """Extract timestamp from log line"""
        time_pattern = r'(\d{2}:\d{2}:\d{2})|(\d{10})|(\d{4}-\d{2}-\d{2})'
        match = re.search(time_pattern, line)
        return match.group(0) if match else "N/A"
    
    def _extract_module(self, line: str) -> str:
        """Extract affected module name from log line"""
        # Look for module names in caps or common RTL module patterns
        modules = ['AHB_Controller', 'Memory_Controller', 'Cache_L1', 'Cache_L2',
                  'Interconnect', 'ALU', 'Control_Unit', 'Data_Path', 'Register_File',
                  'SPI_Interface', 'I2C_Interface', 'UART_Controller', 'GPIO_Controller',
                  'Clock_Domain', 'Reset_Logic']
        
        for module in modules:
            if module in line:
                return module
        
        # Try to extract any module-like identifier
        module_match = re.search(r'[A-Z][a-zA-Z0-9_]*', line)
        return module_match.group(0) if module_match else "Unknown"
    
    def _classify_failure(self, line: str) -> str:
        """Classify failure type based on patterns"""
        for failure_type, pattern in self.failure_patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                return failure_type
        return "unknown"
    
    def _assess_severity(self, line: str) -> str:
        """Assess failure severity"""
        if any(word in line.upper() for word in ['CRITICAL', 'FATAL', 'CRASH']):
            return "CRITICAL"
        elif any(word in line.upper() for word in ['ERROR', 'FAIL', 'ASSERT']):
            return "HIGH"
        elif any(word in line.upper() for word in ['WARNING', 'WARN']):
            return "MEDIUM"
        else:
            return "LOW"
    
    def _extract_category(self, line: str) -> str:
        """Determine if failure is from UVM, SVA, or other category"""
        if re.search(r'\bUVM\b', line, re.IGNORECASE):
            return 'UVM'
        if re.search(r'\bSVA\b|assertion', line, re.IGNORECASE):
            return 'SVA'
        # fallback to generic
        return 'GENERAL'
    
    def _extract_testcase(self, line: str) -> str:
        """Extract testcase ID from log line"""
        test_match = re.search(r'TEST=([a-zA-Z0-9_]+)', line)
        return test_match.group(1) if test_match else "unknown_test"
    
    def _extract_failure_count(self, line: str) -> int:
        """Extract failure count from log line"""
        failures_match = re.search(r'FAILURES=(\d+)', line)
        return int(failures_match.group(1)) if failures_match else 1
    
    def extract_unique_signatures(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract unique failure signatures from parsed logs"""
        
        if df.empty:
            return pd.DataFrame()
        
        # Group by failure type, module and category
        signatures = df.groupby(['failure_type', 'module', 'category']).agg({
            'message': 'count',
            'severity': lambda x: x.mode()[0] if len(x.mode()) > 0 else 'UNKNOWN',
            'timestamp': lambda x: f"{x.min()} to {x.max()}",
            'testcase': lambda x: x.nunique(),  # Count unique testcases affected
            'failure_count': 'sum'  # Sum total failures across all occurrences
        }).rename(columns={
            'message': 'occurrence_count',
            'testcase': 'testcase_impact',
            'failure_count': 'total_failures'
        }).reset_index()
        
        signatures['signature_id'] = signatures.index + 1
        signatures = signatures.sort_values('occurrence_count', ascending=False)
        
        return signatures[['signature_id', 'failure_type', 'module', 'category', 'occurrence_count', 
                          'testcase_impact', 'total_failures', 'severity', 'timestamp']]
