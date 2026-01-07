# src/agents/judge_agent.py
import os
import sys
import re
from src.utils.logger import log_experiment, ActionType

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import run_pytest
from src.utils.code_validator import SANDBOX_DIR


def extract_specific_test_failures(pytest_output: str) -> str:
    """
    Extract the MOST USEFUL information from pytest failures
    
    Returns:
        Formatted string with key failure information
    """
    if not pytest_output or "FAILED" not in pytest_output:
        return ""
    
    failures = []
    lines = pytest_output.split('\n')
    
    # Strategy 1: Assertion errors with expected vs actual
    for i, line in enumerate(lines):
        if 'AssertionError' in line or ('assert' in line.lower() and '==' in line):
            start = max(0, i - 3)
            end = min(len(lines), i + 5)
            context = '\n'.join(lines[start:end])
            if len(context.strip()) > 20:
                failures.append(context)
    
    # Strategy 2: FAILED lines with test details
    for i, line in enumerate(lines):
        if 'FAILED' in line:
            end = min(len(lines), i + 8)
            context = '\n'.join(lines[i:end])
            failures.append(context)
    
    # Strategy 3: Expected vs actual patterns
    for i, line in enumerate(lines):
        if any(word in line.lower() for word in ['expected', 'actual', '!=']):
            start = max(0, i - 1)
            end = min(len(lines), i + 3)
            context = '\n'.join(lines[start:end])
            if len(context.strip()) > 20:
                failures.append(context)
    
    # Remove duplicates
    seen = set()
    unique_failures = []
    for failure in failures:
        if failure not in seen and len(failure.strip()) > 10:
            seen.add(failure)
            unique_failures.append(failure)
    
    if unique_failures:
        return "\n\n---\n\n".join(unique_failures[:3])
    
    # Fallback
    return pytest_output[-600:] if len(pytest_output) > 600 else pytest_output


def parse_pytest_results(pytest_output: str) -> tuple:
    """
    Parse pytest output to extract pass/fail counts
    
    Returns:
        (passed_count, failed_count, has_tests)
    """
    passed_match = re.search(r'(\d+)\s+passed', pytest_output)
    failed_match = re.search(r'(\d+)\s+failed', pytest_output)
    error_match = re.search(r'(\d+)\s+error', pytest_output)
    
    passed_count = int(passed_match.group(1)) if passed_match else 0
    failed_count = int(failed_match.group(1)) if failed_match else 0
    error_count = int(error_match.group(1)) if error_match else 0
    
    has_tests = (passed_count > 0 or failed_count > 0 or error_count > 0)
    
    if not has_tests and "no tests ran" in pytest_output.lower():
        has_tests = False
    
    return passed_count, failed_count + error_count, has_tests


def judge_agent(state: dict) -> dict:
    """
    JUDGE Agent: Executes unit tests and validates fixes
    
    Responsibilities:
    - Execute pytest on fixed code
    - Validate syntax
    - Parse test results
    - Send feedback to Fixer if unsuccessful (Self-Healing Loop)
    - Confirm mission end if successful
    
    Args:
        state: Current workflow state with fixed code
        
    Returns:
        Updated state with test results and validation status
    """
    print("⚖️ [JUDGE] Validating fixes...")
    
    fixed_code = state.get("fixed_code", state["code"])
    file_name = state.get("file_name", "unknown.py")
    iteration = state.get("iteration_count", 0)
    
    # Increment iteration counter
    state["iteration_count"] = iteration + 1
    
    pytest_output = ""
    specific_failures = ""
    syntax_valid = False
    
    # ===================================================================
    # STEP 1: SYNTAX VALIDATION
    # ===================================================================
    try:
        compile(fixed_code, '<string>', 'exec')
        print("   ✅ Syntax valid")
        syntax_valid = True
    except SyntaxError as e:
        print(f"   ❌ SYNTAX ERROR: Line {e.lineno}: {e.msg}")
        
        lines = fixed_code.split('\n')
        if 0 <= e.lineno - 1 < len(lines):
            print(f"      Line {e.lineno}: {lines[e.lineno - 1]}")
        
        syntax_error_details = f"Syntax error at line {e.lineno}: {e.msg}"
        if 0 <= e.lineno - 1 < len(lines):
            syntax_error_details += f"\nProblematic line: {lines[e.lineno - 1]}"
        
        # Update state with syntax error feedback
        state["is_fixed"] = False
        state["pytest_report"] = f"SYNTAX ERROR at line {e.lineno}: {e.msg}"
        state["specific_test_failures"] = syntax_error_details
        state["code"] = fixed_code
        
        log_experiment(
            agent_name="Judge_Agent",
            model_used="validation",
            action=ActionType.GENERATION,
            details={
                "iteration": iteration + 1,
                "syntax_valid": False,
                "syntax_error": str(e),
                "input_prompt": f"Validating syntax (iteration {iteration + 1})",
                "output_response": f"SYNTAX ERROR: {str(e)}"
            },
            status="FAILURE"
        )
        
        print("   🔄 Sending syntax error feedback to Fixer")
        return state
    
    # ===================================================================
    # STEP 2: SAVE FIXED CODE
    # ===================================================================
    try:
        base_name = os.path.splitext(os.path.basename(file_name))[0]
        fixed_file_path = os.path.join(SANDBOX_DIR, f"{base_name}_fixed.py")
        
        os.makedirs(SANDBOX_DIR, exist_ok=True)
        
        with open(fixed_file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_code)
        
        print(f"   💾 Saved to: {fixed_file_path}")
        
    except Exception as e:
        print(f"   ❌ Failed to save file: {e}")
        
        state["is_fixed"] = False
        state["pytest_report"] = f"File save error: {str(e)}"
        state["specific_test_failures"] = f"Could not save fixed code: {str(e)}"
        
        log_experiment(
            agent_name="Judge_Agent",
            model_used="validation",
            action=ActionType.GENERATION,
            details={
                "iteration": iteration + 1,
                "save_error": str(e),
                "input_prompt": f"Saving fixed code (iteration {iteration + 1})",
                "output_response": f"ERROR: {str(e)}"
            },
            status="FAILURE"
        )
        
        return state
    
    # ===================================================================
    # STEP 3: EXECUTE UNIT TESTS
    # ===================================================================
    try:
        print(f"   🧪 Running pytest...")
        pytest_output = run_pytest(fixed_file_path)
        
        # Extract specific failures
        specific_failures = extract_specific_test_failures(pytest_output)
        
        # Store in state
        state["pytest_report"] = pytest_output
        state["specific_test_failures"] = specific_failures
        
        # ===================================================================
        # STEP 4: PARSE TEST RESULTS
        # ===================================================================
        
        passed_count, failed_count, has_tests = parse_pytest_results(pytest_output)
        
        print(f"   📊 Results: {passed_count} passed, {failed_count} failed")
        
        # SUCCESS: All tests passed
        if failed_count == 0 and syntax_valid:
            if has_tests:
                print(f"   ✅ ALL {passed_count} TESTS PASSED!")
            else:
                print(f"   ✅ NO TESTS FOUND, but code is syntactically valid")
            
            state["is_fixed"] = True
            state["refactored_code"] = fixed_code
            
            log_experiment(
                agent_name="Judge_Agent",
                model_used="validation",
                action=ActionType.GENERATION,
                details={
                    "iteration": iteration + 1,
                    "tests_passed": True,
                    "syntax_valid": True,
                    "passed_count": passed_count,
                    "failed_count": failed_count,
                    "has_tests": has_tests,
                    "input_prompt": f"Running pytest (iteration {iteration + 1})",
                    "output_response": f"SUCCESS: {passed_count} passed, {failed_count} failed"
                },
                status="SUCCESS"
            )
            
            print(f"\n{'='*60}")
            print(f"🎉 MISSION COMPLETE after {iteration + 1} iteration(s)!")
            print(f"{'='*60}\n")
            
            return state
        
        # FAILURE: Tests failed - send back to Fixer
        else:
            print(f"   ❌ {failed_count} TEST(S) FAILED")
            
            if specific_failures:
                print(f"\n   📋 SPECIFIC FAILURES (sending to Fixer):")
                print(f"   {'-'*50}")
                for line in specific_failures.split('\n')[:10]:
                    if line.strip():
                        print(f"   {line}")
                print(f"   {'-'*50}\n")
            
            state["is_fixed"] = False
            state["code"] = fixed_code  # Update code for next iteration
    
    except Exception as e:
        print(f"   ❌ Test execution error: {e}")
        pytest_output = f"Test execution failed: {str(e)}"
        specific_failures = f"Test execution error: {str(e)}"
        state["pytest_report"] = pytest_output
        state["specific_test_failures"] = specific_failures
        state["is_fixed"] = False
        state["code"] = fixed_code
    
    # ===================================================================
    # STEP 5: LOG FAILURE AND PREPARE FOR NEXT ITERATION
    # ===================================================================
    
    log_experiment(
        agent_name="Judge_Agent",
        model_used="validation",
        action=ActionType.GENERATION,
        details={
            "iteration": iteration + 1,
            "tests_passed": False,
            "syntax_valid": syntax_valid,
            "pytest_output_preview": pytest_output[:300] if pytest_output else "N/A",
            "has_specific_failures": bool(specific_failures),
            "input_prompt": f"Running pytest (iteration {iteration + 1})",
            "output_response": pytest_output[:500] if pytest_output else "No output"
        },
        status="PARTIAL"
    )
    
    print(f"❌ Tests failed (Iteration {iteration + 1})")
    
    if iteration + 1 >= state.get("max_iterations", 3):
        print(f"   🛑 Max iterations ({state.get('max_iterations', 3)}) reached")
        print("   ⚠️ Mission incomplete - manual review required")
    else:
        print(f"   🔄 Sending feedback to Fixer (iteration {iteration + 2}/{state.get('max_iterations', 3)})")
    
    return state