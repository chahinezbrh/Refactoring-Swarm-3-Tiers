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
    curr_iteration = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 20)

    if curr_iteration < 0:
        print(f"⚠️ Bad iteration_count ({curr_iteration}), resetting to 0")
        curr_iteration = 0

    if max_iterations <= 0:
        print(f"⚠️ Invalid max_iterations ({max_iterations}), defaulting to 20")
        max_iterations = 20

    def _log_success():
        print(f"\n{'='*70}")
        print(f"🎉 MISSION COMPLETE: All tests passed!")
        print(f"   Total iterations: {curr_iteration}")
        print(f"{'='*70}\n")

    def _log_max_reached():
        print(f"\n{'='*70}")
        print(f"⚠️ MAX ITERATIONS REACHED: {max_iterations}")
        print(f"   Status: Tests still failing")
        print(f"   Action: Cannot iterate again - manual review required")
        print(f"{'='*70}\n")

    def _log_continue():
        print(f"\n{'='*70}")
        print(f"🔄 SELF-HEALING LOOP ACTIVATED")
        print(f"   Current iteration: {curr_iteration}")
        print(f"   Next iteration: {curr_iteration + 1}/{max_iterations}")
        print(f"   Action: Sending test failures back to Auditor")
        print(f"{'='*70}\n")

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

    # Ordered rules table: first matching condition wins.
    rules = [
        (state.get("is_fixed", False),      "end",      _log_success),
        (curr_iteration >= max_iterations,  "end",      _log_max_reached),
        (True,                               "auditor",  _log_continue),
    ]

    for condition, outcome, log_fn in rules:
        if condition:
            log_fn()
            return outcome
def get_workflow_status(state: dict) -> dict:
    """
    Get a summary of the current workflow status
    
    Args:
        state: Current workflow state
        
    Returns:
        Dictionary with status information
    """
    # Default aligned with should_continue()'s default (20) — these two
    # functions must agree on "max_iterations" when the key is missing from
    # state, or a status display could report a different ceiling than the
    # one should_continue() is actually enforcing.
    current_iteration = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 20)

    return {
        "iteration": current_iteration,
        "max_iterations": max_iterations,
        "iterations_remaining": max(0, max_iterations - current_iteration),
        "is_fixed": state.get("is_fixed", False),
        "has_test_failures": bool(state.get("specific_test_failures")),
        "pytest_report_available": bool(state.get("pytest_report")),
        "refactoring_plan_available": bool(state.get("refactoring_plan"))
    }