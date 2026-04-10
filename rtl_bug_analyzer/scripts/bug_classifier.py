"""
Bug Classifier - Categorize and prioritize bugs for fixing
"""

import pandas as pd
from typing import Dict, List
import json


class BugClassifier:
    """Classify bugs by priority based on recurrence and testcase impact"""
    
    def __init__(self):
        pass
    
    def classify_bugs(self, signatures_df: pd.DataFrame) -> pd.DataFrame:
        """Classify signatures based on recurrence count and testcase impact"""
        
        bugs = []
        
        for _, sig in signatures_df.iterrows():
            bug = {
                'signature_id': sig['signature_id'],
                'failure_type': sig['failure_type'],
                'module': sig['module'],
                'recurrence_count': sig['occurrence_count'],
                'testcase_impact': sig['testcase_impact'],
                'total_failures': sig['total_failures'],
                'severity': sig['severity'],
                'timestamp': sig['timestamp'],
            }
            
            # Simple priority calculation: recurrence × testcase impact
            # Higher = more critical (affects more tests and happens more often)
            priority_score = sig['occurrence_count'] * sig['testcase_impact']
            
            bug['priority_score'] = priority_score
            bug['impact_level'] = self._rate_impact(sig['testcase_impact'])
            
            bugs.append(bug)
        
        # Create dataframe and sort by priority
        bugs_df = pd.DataFrame(bugs)
        bugs_df = bugs_df.sort_values('priority_score', ascending=False)
        
        return bugs_df
    
    def _rate_impact(self, score) -> str:
        """Rate testcase impact level"""
        if score >= 4:
            return "Very High"
        elif score >= 3:
            return "High"
        elif score >= 2:
            return "Medium"
        else:
            return "Low"
