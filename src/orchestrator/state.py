# src/orchestrator/state.py
# State schema definition

from typing import TypedDict, List, Dict, Any


class State(TypedDict, total=False):  # FIX: Added total=False to make all fields optional
    """State passed between agents in the refactoring workflow"""
    code: str                           
    file_name: str                      
    analysis_result: str                
    debug_info: str                     # Output from debug agent
    fixed_code: str                     # Output from fix agent
    is_fixed: bool                      # Whether code passes validation
    iteration_count: int                # Current iteration number
    max_iterations: int                 # Maximum allowed iterations
    messages: List[Dict[str, str]]      # Message history
    refactored_code: str                # Refactored code output
    pylint_report: str                  # Pylint analysis report
    pytest_report: str                  # Pytest test results
    refactoring_plan: str
    specific_test_failures: str
    pattern_detection: str




      