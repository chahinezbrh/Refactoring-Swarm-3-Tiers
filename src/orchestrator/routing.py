# src/orchestrator/routing.py
# Routing logic for the 3-agent self-healing workflow

from typing import Literal
from .state import State


def should_continue(state: dict) -> str:
    """
    Determine whether to continue the self-healing loop or end the mission
    
    REQUIREMENTS:
    1. ALWAYS stop when is_fixed=True (file is fixed, tests passed)
    2. ALWAYS stop when iteration_count >= max_iterations (cannot iterate again)
    3. Continue otherwise (more iterations available)
    
    Args:
        state: Current workflow state with test results
        
    Returns:
        "end": Terminate workflow (success or max iterations)
        "auditor": Loop back to Auditor for re-analysis (self-healing)
    """
    # Get current iteration count
    current_iteration = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 10)
    
    # ================================================================
    # RULE 1: If tests passed, STOP immediately (SUCCESS)
    # ================================================================
    if state.get("is_fixed", False):
        print(f"\n{'='*70}")
        print(f"🎉 MISSION COMPLETE: All tests passed!")
        print(f"   Total iterations: {current_iteration}")
        print(f"{'='*70}\n")
        return "end"
    
    # ================================================================
    # RULE 2: If max iterations reached, STOP (cannot iterate again)
    # ================================================================
    if current_iteration >= max_iterations:
        print(f"\n{'='*70}")
        print(f"⚠️ MAX ITERATIONS REACHED: {max_iterations}")
        print(f"   Status: Tests still failing")
        print(f"   Action: Cannot iterate again - manual review required")
        print(f"{'='*70}\n")
        return "end"
    
    # ================================================================
    # RULE 3: Continue to next iteration (more attempts available)
    # ================================================================
    print(f"\n{'='*70}")
    print(f"🔄 SELF-HEALING LOOP ACTIVATED")
    print(f"   Current iteration: {current_iteration}")
    print(f"   Next iteration: {current_iteration + 1}/{max_iterations}")
    print(f"   Action: Sending test failures back to Auditor")
    print(f"{'='*70}\n")
    
    # Show what feedback is being sent
    specific_failures = state.get("specific_test_failures", "")
    if specific_failures:
        print("📋 Feedback for Auditor:")
        print("-" * 70)
        preview = specific_failures.split('\n')[:5]
        for line in preview:
            if line.strip():
                print(f"   {line}")
        if len(specific_failures.split('\n')) > 5:
            print("   ...")
        print("-" * 70 + "\n")
    
    return "auditor"


def get_workflow_status(state: dict) -> dict:
    """
    Get a summary of the current workflow status
    
    Args:
        state: Current workflow state
        
    Returns:
        Dictionary with status information
    """
    return {
        "iteration": state.get("iteration_count", 0),
        "max_iterations": state.get("max_iterations", 10),
        "is_fixed": state.get("is_fixed", False),
        "has_test_failures": bool(state.get("specific_test_failures")),
        "pytest_report_available": bool(state.get("pytest_report")),
        "refactoring_plan_available": bool(state.get("refactoring_plan"))
    }