# src/orchestrator/routing.py
# Routing logic for the 3-agent self-healing workflow

from typing import Literal
from .state import State



Here's a version with only syntactic changes — variable renames, formatting, minor restructuring — with the exact same logic and behavior:

python
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
    # Pull the iteration limits out of state
    iteration_limit = state.get("max_iterations", 20)
    current_iter = state.get("iteration_count", 0)

    # Sanity-check iteration_count before using it below
    if current_iter < 0:
        print(f"⚠️ iteration_count looked wrong ({current_iter}), resetting to 0")
        current_iter = 0

    # ================================================================
    # RULE 1: If tests passed, STOP immediately (SUCCESS)
    # ================================================================
    tests_passed = state.get("is_fixed", False)
    if tests_passed:
        print(f"\n{'='*70}")
        print(f"🎉 MISSION COMPLETE: All tests passed!")
        print(f"   Total iterations: {current_iter}")
        print(f"{'='*70}\n")
        return "end"

    # ================================================================
    # RULE 2: If max iterations reached, STOP (cannot iterate again)
    # ================================================================
    if current_iter >= iteration_limit:
        print(f"\n{'='*70}")
        print(f"⚠️ MAX ITERATIONS REACHED: {iteration_limit}")
        print(f"   Status: Tests still failing")
        print(f"   Action: Cannot iterate again - manual review required")
        print(f"{'='*70}\n")
        return "end"

    # ================================================================
    # RULE 3: Continue to next iteration (more attempts available)
    # ================================================================
    print(f"\n{'='*70}")
    print(f"🔄 SELF-HEALING LOOP ACTIVATED")
    print(f"   Current iteration: {current_iter}")
    print(f"   Next iteration: {current_iter + 1}/{iteration_limit}")
    print(f"   Action: Sending test failures back to Auditor")
    print(f"{'='*70}\n")

    # Show what feedback is being sent
    specific_failures = state.get("specific_test_failures", "")
    if specific_failures:
        print("📋 Feedback for Auditor:")
        print("-" * 70)
        failure_lines = specific_failures.split('\n')
        preview = failure_lines[:5]
        for line in preview:
            if line.strip():
                print(f"   {line}")
        if len(failure_lines) > 5:
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
    # Default aligned with should_continue()'s default (20) — these two
    # functions must agree on "max_iterations" when the key is missing from
    # state, or a status display could report a different ceiling than the
    # one should_continue() is actually enforcing.
    max_iterations = state.get("max_iterations", 20)
    current_iteration = state.get("iteration_count", 0)

    return {
        "iteration": current_iteration,
        "max_iterations": max_iterations,
        "iterations_remaining": max(0, max_iterations - current_iteration),
        "is_fixed": state.get("is_fixed", False),
        "has_test_failures": bool(state.get("specific_test_failures")),
        "pytest_report_available": bool(state.get("pytest_report")),
        "refactoring_plan_available": bool(state.get("refactoring_plan"))
    }