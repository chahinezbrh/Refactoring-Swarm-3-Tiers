# src/orchestrator/routing.py
# Routing logic for the 3-agent self-healing workflow

from typing import Literal
from .state import State

DEFAULT_MAX_ITERATIONS = 20


def _read_limits(state: dict, warn: bool = False) -> tuple[int, int]:
    """
    Single source of truth for reading and validating iteration counters.
    Used by both should_continue() and get_workflow_status() so they always
    agree on the iteration count and the enforced ceiling.

    Args:
        state: Current workflow state
        warn: Print a warning when an invalid value is corrected

    Returns:
        (current_iteration, max_iterations), both validated
    """
    curr_iteration = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", DEFAULT_MAX_ITERATIONS)

    if curr_iteration < 0:
        if warn:
            print(f"⚠️ Bad iteration_count ({curr_iteration}), resetting to 0")
        curr_iteration = 0

    if max_iterations <= 0:
        if warn:
            print(
                f"⚠️ Invalid max_iterations ({max_iterations}), "
                f"defaulting to {DEFAULT_MAX_ITERATIONS}"
            )
        max_iterations = DEFAULT_MAX_ITERATIONS

    return curr_iteration, max_iterations


def should_continue(state: dict) -> Literal["end", "auditor"]:
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
    curr_iteration, max_iterations = _read_limits(state, warn=True)

    separator = "=" * 70

    # Rule 1: success
    if state.get("is_fixed", False):
        print(f"\n{separator}")
        print("🎉 MISSION COMPLETE: All tests passed!")
        print(f"   Total iterations: {curr_iteration}")
        print(f"{separator}\n")
        return "end"

    # Rule 2: iteration limit
    if curr_iteration >= max_iterations:
        print(f"\n{separator}")
        print(f"⚠️ MAX ITERATIONS REACHED: {max_iterations}")
        print("   Status: Tests still failing")
        print("   Action: Cannot iterate again - manual review required")
        print(f"{separator}\n")
        return "end"

    # Rule 3: keep looping
    print(f"\n{separator}")
    print("🔄 SELF-HEALING LOOP ACTIVATED")
    print(f"   Current iteration: {curr_iteration}")
    print(f"   Next iteration: {curr_iteration + 1}/{max_iterations}")
    print("   Action: Sending test failures back to Auditor")
    print(f"{separator}\n")

    specific_failures = state.get("specific_test_failures", "")
    if specific_failures:
        lines = specific_failures.split("\n")
        print("📋 Feedback for Auditor:")
        print("-" * 70)
        for line in lines[:5]:
            if line.strip():
                print(f"   {line}")
        if len(lines) > 5:
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
    # Uses the same validation as should_continue(), so the status display
    # always reports the ceiling that is actually being enforced.
    current_iteration, max_iterations = _read_limits(state)

    return {
        "iteration": current_iteration,
        "max_iterations": max_iterations,
        "iterations_remaining": max(0, max_iterations - current_iteration),
        "is_fixed": state.get("is_fixed", False),
        "has_test_failures": bool(state.get("specific_test_failures")),
        "pytest_report_available": bool(state.get("pytest_report")),
        "refactoring_plan_available": bool(state.get("refactoring_plan")),
    }