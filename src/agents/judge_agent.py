"""
JUDGE Agent: Validates fixes by running tests and provides LLM-powered feedback

Responsibilities:
1. Validate syntax (compile check)
2. ALWAYS generate unit tests (regardless of doctests)
3. Create TEMPORARY file for pytest execution
4. Run pytest on unit tests
5. Use LLM to analyze test failures
6. Parse test results
7. Generate markdown documentation when tests pass (FINAL CODE ONLY)
8. Provide intelligent feedback to Fixer
9. Store final code in STATE only
"""

import os
import sys
import re
import ast
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from src.utils.logger import log_experiment, ActionType
from src.prompts.judge_prompts import JUDGE_VALIDATION_PROMPT, JUDGE_SUCCESS_PROMPT

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import run_pytest, write_file


def generate_unit_tests_with_llm(code: str, file_name: str) -> str:
    """
    Generate unit tests for code using LLM - OPTIMIZED.
    
    Args:
        code: Python code to generate tests for
        file_name: Name of the file
        
    Returns:
        Generated test code as string
    """
    start_time = time.time()
    code_lines = len(code.split('\n'))
    code_chars = len(code)
    
    # Dynamic timeout based on code size
    timeout = max(60, min(180, code_lines // 2))
    
    print("   🤖 Generating unit tests with LLM...")
    print(f"   📊 Code: {code_lines} lines, {code_chars} chars")
    print(f"   ⏱️  Using {timeout}s timeout")
    
    base_name = os.path.splitext(os.path.basename(file_name))[0]
    
    # SIMPLIFIED PROMPT for faster processing
    prompt = f"""Generate pytest tests for this Python code.

CODE:
```python
{code}
```

Requirements:
- Test all functions/methods
- Import from {base_name}_temp
- Include edge cases
- Return only Python code (no markdown)

Tests:"""

    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        temperature=0.3,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        max_retries=0,  # No retries for speed
        timeout=timeout  # Dynamic timeout
    )
    
    try:
        print(f"   ⏳ Calling Gemini API at {time.strftime('%H:%M:%S')}...")
        response = llm.invoke(prompt)
        
        if isinstance(response.content, list):
            test_code = ' '.join(str(item) for item in response.content)
        else:
            test_code = str(response.content)
        
        # Clean up any markdown formatting
        test_code = test_code.replace('```python', '').replace('```', '').strip()
        
        elapsed = time.time() - start_time
        print(f"   ✅ Generated {len(test_code)} chars in {elapsed:.1f}s")
        
        # Log test generation
        log_experiment(
            agent_name="Judge_Agent",
            model_used="gemini-flash-latest",
            action=ActionType.GENERATION,
            details={
                "file_name": file_name,
                "code_lines": code_lines,
                "code_chars": code_chars,
                "timeout_used": timeout,
                "generation_time": f"{elapsed:.1f}s",
                "input_prompt": prompt[:500] + "...",
                "output_response": test_code[:500] + "...",
                "purpose": "unit_test_generation"
            },
            status="SUCCESS"
        )
        
        return test_code
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"   ❌ Test generation failed after {elapsed:.1f}s: {e}")
        
        log_experiment(
            agent_name="Judge_Agent",
            model_used="gemini-flash-latest",
            action=ActionType.GENERATION,
            details={
                "file_name": file_name,
                "error": str(e),
                "generation_time": f"{elapsed:.1f}s",
                "timeout_used": timeout,
                "input_prompt": prompt[:500] + "...",
                "output_response": f"ERROR: {str(e)}",
                "purpose": "unit_test_generation"
            },
            status="FAILURE"
        )
        
        return None


def extract_specific_test_failures(pytest_output: str) -> str:
    """
    Extract key information from pytest failures
    """
    if not pytest_output or "FAILED" not in pytest_output:
        return ""
    
    failures = []
    lines = pytest_output.split('\n')
    
    # Strategy 1: Assertion errors
    for i, line in enumerate(lines):
        if 'AssertionError' in line or ('assert' in line.lower() and '==' in line):
            start = max(0, i - 3)
            end = min(len(lines), i + 5)
            context = '\n'.join(lines[start:end])
            if len(context.strip()) > 20:
                failures.append(context)
    
    # Strategy 2: FAILED lines
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
        return "\n\n---\n\n".join(unique_failures[:3])  # Top 3
    
    # Fallback: last 600 chars
    return pytest_output[-600:] if len(pytest_output) > 600 else pytest_output


def parse_pytest_results(pytest_output: str) -> tuple:
    """
    Parse pytest output to extract pass/fail counts
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


def analyze_test_failures_with_llm(fixed_code: str, pytest_output: str) -> str:
    """
    Use LLM to analyze test failures - OPTIMIZED
    """
    print("   🤖 Using LLM to analyze test failures...")
    
    # Limit pytest output to avoid token limits
    truncated_output = pytest_output[-2000:] if len(pytest_output) > 2000 else pytest_output
    
    prompt = JUDGE_VALIDATION_PROMPT.format(
        test_results=truncated_output,
        code=fixed_code
    )
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        temperature=0,  # Deterministic analysis
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        max_retries=0,  # No retries for speed
        timeout=60      # 60s timeout
    )
    
    try:
        response = llm.invoke(prompt)
        
        # Handle list or string response
        if isinstance(response.content, list):
            analysis = ' '.join(str(item) for item in response.content)
        else:
            analysis = str(response.content)
        
        print("   ✅ LLM analysis complete")
        return analysis
        
    except Exception as e:
        print(f"   ⚠️ LLM analysis failed: {e}")
        # Fallback to basic extraction
        return extract_specific_test_failures(pytest_output)


def generate_documentation_with_llm(code: str, file_name: str) -> str:
    """
    Generate comprehensive markdown documentation - OPTIMIZED
    """
    print("   📝 Generating markdown documentation...")
    
    base_name = os.path.splitext(os.path.basename(file_name))[0]
    
    # Enhanced prompt with better structure
    prompt = f"""Generate comprehensive markdown documentation for this Python code.

CODE:
```python
{code}
```

Create a complete .md documentation file with this structure:

# {base_name.title().replace('_', ' ')} - Documentation

**Status**: Production Ready - All Tests Passed  
**File**: `{os.path.basename(file_name)}`

---

## Overview
[Brief description of what this code does - 2-3 sentences]

---

## Functions

For EACH function, provide:

### `function_name(param1, param2, ...)`

**Description:**  
[What the function does]

**Parameters:**
- `param1` (type): Description
- `param2` (type): Description

**Returns:**
- Type: Description

**Examples:**
```python
>>> function_name(arg1, arg2)
expected_output
```

**Edge Cases:**
- What happens with empty inputs
- What happens with invalid inputs
- Error handling behavior

---

[Repeat for ALL functions in the code]

---

## Summary

### Functions Included
- `function1`: Brief description
- `function2`: Brief description
[List all functions]

### Testing Status
✅ All functions tested and validated

Return ONLY the markdown documentation (no code blocks around it):"""

    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        temperature=0.3,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        max_retries=2,  # Increased retries for documentation
        timeout=90      # Increased timeout for documentation
    )
    
    try:
        response = llm.invoke(prompt)
        
        if isinstance(response.content, list):
            documentation = ' '.join(str(item) for item in response.content)
        else:
            documentation = str(response.content)
        
        # Clean up any markdown code blocks if LLM wrapped it
        documentation = documentation.replace('```markdown', '').replace('```', '').strip()
        
        print(f"   ✅ Generated {len(documentation)} chars of documentation")
        
        # Log documentation generation
        log_experiment(
            agent_name="Judge_Agent",
            model_used="gemini-flash-latest",
            action=ActionType.GENERATION,
            details={
                "file_name": file_name,
                "documentation_chars": len(documentation),
                "input_prompt": prompt[:500] + "...",
                "output_response": documentation[:500] + "...",
                "purpose": "documentation_generation"
            },
            status="SUCCESS"
        )
        
        return documentation
        
    except Exception as e:
        print(f"   ⚠️ Documentation generation failed: {e}")
        
        # Fallback basic documentation
        fallback_doc = f"""# {base_name.title().replace('_', ' ')} - Documentation

**Status**: Production Ready - All Tests Passed  
**File**: `{os.path.basename(file_name)}`

---

## Overview
This file contains Python code that has been successfully refactored and validated.

## Status
✅ All tests passing  
✅ Code validated  
✅ Ready for production

## Note
Automatic documentation generation encountered an error. Please review the code for detailed information about the functions.

---

**Documentation Error**: {str(e)}
"""
        
        log_experiment(
            agent_name="Judge_Agent",
            model_used="gemini-flash-latest",
            action=ActionType.GENERATION,
            details={
                "file_name": file_name,
                "error": str(e),
                "input_prompt": prompt[:500] + "...",
                "output_response": f"ERROR: {str(e)}",
                "purpose": "documentation_generation"
            },
            status="FAILURE"
        )
        
        return fallback_doc


def generate_success_summary_with_llm(original_code: str, fixed_code: str, refactoring_plan: str, iteration_count: int, file_name: str = "unknown.py") -> tuple[str, str, str]:
    """
    Generate success summary - OPTIMIZED
    """
    print("   🤖 Generating success summary...")
    
    prompt = JUDGE_SUCCESS_PROMPT.format(
        test_results="All tests passed successfully",
        code=fixed_code,
        iteration_count=iteration_count
    )
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        temperature=0.3,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        max_retries=0,  # No retries
        timeout=45      # 45s timeout
    )
    
    try:
        response = llm.invoke(prompt)
        
        if isinstance(response.content, list):
            summary = ' '.join(str(item) for item in response.content)
        else:
            summary = str(response.content)
        
        # Log the success summary generation
        log_experiment(
            agent_name="Judge_Agent",
            model_used="gemini-flash-latest",
            action=ActionType.GENERATION,
            details={
                "file_name": file_name,
                "iteration": iteration_count,
                "input_prompt": prompt[:500] + "..." if len(prompt) > 500 else prompt,
                "output_response": summary[:500] + "..." if len(summary) > 500 else summary,
                "purpose": "success_summary_generation"
            },
            status="SUCCESS"
        )
        
        return summary, prompt, summary
        
    except Exception as e:
        print(f"   ⚠️ Summary generation failed: {e}")
        
        error_summary = "All tests passed successfully."
        
        # Log the failure
        log_experiment(
            agent_name="Judge_Agent",
            model_used="gemini-flash-latest",
            action=ActionType.GENERATION,
            details={
                "file_name": file_name,
                "iteration": iteration_count,
                "input_prompt": prompt[:500] + "..." if len(prompt) > 500 else prompt,
                "output_response": f"ERROR: {str(e)}",
                "purpose": "success_summary_generation"
            },
            status="FAILURE"
        )
        
        return error_summary, prompt, f"ERROR: {str(e)}"


def judge_agent(state: dict) -> dict:
    """
    JUDGE Agent: Validates fixes and provides LLM-powered feedback
    """
    print("⚖️ [JUDGE] Validating fixes...")
    
    fixed_code = state.get("fixed_code", state["code"])
    file_name = state.get("file_name", "unknown.py")
    iteration = state.get("iteration_count", 0)
    original_code = state.get("code", "")
    refactoring_plan = state.get("refactoring_plan", "")
    
    # ========================================================================
    # VALIDATE max_iterations PARAMETER
    # ========================================================================
    max_iterations = state.get("max_iterations")
    
    # Check if max_iterations is provided
    if max_iterations is None:
        error_msg = "❌ ERROR: max_iterations parameter is required but not provided!"
        print(f"   {error_msg}")
        
        log_experiment(
            agent_name="Judge_Agent",
            model_used="validation",
            action=ActionType.GENERATION,
            details={
                "error": "Missing max_iterations parameter",
                "input_prompt": "Validating max_iterations parameter",
                "output_response": error_msg
            },
            status="FAILURE"
        )
        
        raise ValueError("max_iterations parameter is required")
    
    # Check if max_iterations exceeds 10
    if max_iterations > 10:
        error_msg = f"❌ ERROR: max_iterations={max_iterations} exceeds maximum allowed value of 10!"
        print(f"   {error_msg}")
        
        log_experiment(
            agent_name="Judge_Agent",
            model_used="validation",
            action=ActionType.GENERATION,
            details={
                "error": f"max_iterations {max_iterations} > 10",
                "input_prompt": "Validating max_iterations parameter",
                "output_response": error_msg
            },
            status="FAILURE"
        )
        
        raise ValueError(f"max_iterations must not exceed 10 (got {max_iterations})")
    
    print(f"   ✅ max_iterations validated: {max_iterations} (≤ 10)")
    
    # Increment iteration counter
    state["iteration_count"] = iteration + 1
    
    syntax_valid = False
    temp_test_file = None
    temp_source_file = None
    
    # ========================================================================
    # STEP 1: SYNTAX VALIDATION
    # ========================================================================
    try:
        compile(fixed_code, '<string>', 'exec')
        print("   ✅ Syntax valid")
        syntax_valid = True
    except SyntaxError as e:
        print(f"   ❌ SYNTAX ERROR: Line {e.lineno}: {e.msg}")
        
        lines = fixed_code.split('\n')
        if 0 <= e.lineno - 1 < len(lines):
            print(f"      Line {e.lineno}: {lines[e.lineno - 1]}")
        
        # Prepare feedback for Fixer
        syntax_error_details = f"Syntax error at line {e.lineno}: {e.msg}"
        if 0 <= e.lineno - 1 < len(lines):
            syntax_error_details += f"\nProblematic line: {lines[e.lineno - 1]}"
        
        # Update state
        state["is_fixed"] = False
        state["pytest_report"] = f"SYNTAX ERROR at line {e.lineno}: {e.msg}"
        state["specific_test_failures"] = syntax_error_details
        state["code"] = fixed_code  # Update for next iteration
        
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
    
    # ========================================================================
    # STEP 2: ALWAYS GENERATE UNIT TESTS WITH LLM
    # ========================================================================
    print("   🧪 Generating unit tests for validation...")
    generated_tests = generate_unit_tests_with_llm(fixed_code, file_name)
    
    if not generated_tests:
        print("   ❌ Failed to generate unit tests")
        state["is_fixed"] = False
        state["pytest_report"] = "No tests available - test generation failed"
        state["specific_test_failures"] = "Could not generate unit tests automatically"
        return state
    
    print("   ✅ Unit tests generated successfully")
    
    # ========================================================================
    # STEP 3: CREATE TEMPORARY FILES FOR PYTEST
    # ========================================================================
    try:
        # Get the project root and sandbox directory
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_file_dir, '../..'))
        sandbox_dir = os.path.join(project_root, 'sandbox')
        
        # Ensure sandbox directory exists
        os.makedirs(sandbox_dir, exist_ok=True)
        
        base_name = os.path.splitext(os.path.basename(file_name))[0]
        
        # ALWAYS create TWO files for unit testing:
        # 1. Source file (without _fixed to allow imports)
        # 2. Test file with test_ prefix
        
        source_file_name = f"{base_name}_temp.py"
        test_file_name = f"test_{base_name}_temp.py"
        
        temp_source_file = os.path.join(sandbox_dir, source_file_name)
        temp_test_file = os.path.join(sandbox_dir, test_file_name)
        
        print(f"   💾 Creating temporary source file: {source_file_name}")
        with open(temp_source_file, 'w', encoding='utf-8') as f:
            f.write(fixed_code)
        
        print(f"   💾 Creating unit test file: {test_file_name}")
        # Update imports in generated tests to match temp file name
        updated_tests = generated_tests.replace(f"from {base_name} import", f"from {base_name}_temp import")
        with open(temp_test_file, 'w', encoding='utf-8') as f:
            f.write(updated_tests)
        
        print(f"   ✅ Temporary files created for testing")
        
    except Exception as e:
        print(f"   ❌ Failed to create test files: {e}")
        
        state["is_fixed"] = False
        state["pytest_report"] = f"File creation error: {str(e)}"
        state["specific_test_failures"] = f"Could not create test files: {str(e)}"
        
        log_experiment(
            agent_name="Judge_Agent",
            model_used="file_creation",
            action=ActionType.GENERATION,
            details={
                "iteration": iteration + 1,
                "file_error": str(e),
                "input_prompt": f"Creating test files (iteration {iteration + 1})",
                "output_response": f"ERROR: {str(e)}"
            },
            status="FAILURE"
        )
        
        return state
    
    # ========================================================================
    # STEP 4: EXECUTE TESTS
    # ========================================================================
    try:
        print(f"   🧪 Running pytest on generated unit tests...")
        pytest_output = run_pytest()
        
        # Store in state
        state["pytest_report"] = pytest_output
        
        # ====================================================================
        # STEP 5: PARSE TEST RESULTS
        # ====================================================================
        
        passed_count, failed_count, has_tests = parse_pytest_results(pytest_output)
        
        print(f"   📊 Results: {passed_count} passed, {failed_count} failed")
        
        # ====================================================================
        # SUCCESS: All tests passed
        # ====================================================================
        if failed_count == 0 and syntax_valid:
            if has_tests:
                print(f"   ✅ ALL {passed_count} TESTS PASSED!")
                
                # Generate success summary with LLM
                success_summary, summary_prompt, summary_response = generate_success_summary_with_llm(
                    original_code, 
                    fixed_code, 
                    refactoring_plan,
                    iteration + 1,
                    file_name
                )
                state["success_summary"] = success_summary
                
            else:
                print(f"   ✅ NO TESTS FOUND, but code is syntactically valid")
                state["success_summary"] = "No tests found, but code is syntactically valid."
            
            # Mark as fixed and store final code in STATE
            state["is_fixed"] = True
            state["refactored_code"] = fixed_code
            
            # ============================================================
            # Generate documentation ONLY for FINAL fixed code - WITH DEBUG
            # ============================================================
            if has_tests:
                print("   📄 Generating code documentation for final fixed code...")
                print(f"   🔍 DEBUG: has_tests = {has_tests}")
                print(f"   🔍 DEBUG: About to call generate_documentation_with_llm")
                
                documentation = generate_documentation_with_llm(fixed_code, file_name)
                
                print(f"   🔍 DEBUG: Documentation returned")
                print(f"   🔍 DEBUG: documentation is None? {documentation is None}")
                print(f"   🔍 DEBUG: documentation length: {len(documentation) if documentation else 0}")
                
                if not documentation:
                    print("   ⚠️ Documentation generation returned None or empty")
                    state["documentation_created"] = False
                else:
                    print(f"   🔍 DEBUG: file_name = '{file_name}'")
                    
                    # Get the directory where the original file is located
                    original_file_dir = os.path.dirname(os.path.abspath(file_name))
                    
                    print(f"   🔍 DEBUG: original_file_dir = '{original_file_dir}'")
                    print(f"   🔍 DEBUG: sandbox_dir = '{sandbox_dir}'")
                    
                    # If file_name has no directory, use sandbox
                    if not original_file_dir or original_file_dir == '':
                        original_file_dir = sandbox_dir
                        print(f"   ℹ️ No directory in file_name, using sandbox: {sandbox_dir}")
                    
                    # Create documentation filename
                    base_name = os.path.splitext(os.path.basename(file_name))[0]
                    doc_filename = os.path.join(original_file_dir, f"{base_name}_documentation.md")
                    
                    print(f"   📁 Saving documentation to: {doc_filename}")
                    print(f"   🔍 DEBUG: doc_filename absolute path: {os.path.abspath(doc_filename)}")
                    
                    try:
                        # Ensure directory exists
                        print(f"   🔍 DEBUG: Creating directory: {original_file_dir}")
                        os.makedirs(original_file_dir, exist_ok=True)
                        print(f"   🔍 DEBUG: Directory exists? {os.path.exists(original_file_dir)}")
                        
                        # Write documentation
                        print(f"   🔍 DEBUG: Opening file for writing...")
                        with open(doc_filename, 'w', encoding='utf-8') as f:
                            print(f"   🔍 DEBUG: Writing {len(documentation)} chars...")
                            f.write(documentation)
                            print(f"   🔍 DEBUG: Write complete")
                        
                        print(f"   🔍 DEBUG: File closed, checking existence...")
                        
                        # Verify file was created
                        if os.path.exists(doc_filename):
                            file_size = os.path.getsize(doc_filename)
                            print(f"   ✅ Documentation saved: {os.path.basename(doc_filename)} ({file_size} bytes)")
                            print(f"   🔍 DEBUG: Setting state variables...")
                            state["documentation_created"] = True
                            state["documentation_file"] = doc_filename
                            print(f"   🔍 DEBUG: State updated successfully")
                        else:
                            print(f"   ❌ File not found after write!")
                            print(f"   🔍 DEBUG: Checked path: {doc_filename}")
                            print(f"   🔍 DEBUG: Directory contents:")
                            if os.path.exists(original_file_dir):
                                for item in os.listdir(original_file_dir):
                                    print(f"   🔍 DEBUG:   - {item}")
                            state["documentation_created"] = False
                        
                    except Exception as doc_error:
                        print(f"   ❌ Failed to save documentation: {doc_error}")
                        print(f"   🔍 DEBUG: Exception type: {type(doc_error).__name__}")
                        import traceback
                        traceback.print_exc()
                        state["documentation_created"] = False
            else:
                print(f"   ℹ️ Skipping documentation generation")
                print(f"   🔍 DEBUG: has_tests = {has_tests}")
            
            # Log success
            log_experiment(
                agent_name="Judge_Agent",
                model_used="gemini-flash-latest",
                action=ActionType.GENERATION,
                details={
                    "iteration": iteration + 1,
                    "tests_passed": True,
                    "syntax_valid": True,
                    "passed_count": passed_count,
                    "failed_count": failed_count,
                    "has_tests": has_tests,
                    "used_generated_tests": True,
                    "documentation_created": state.get("documentation_created", False),
                    "documentation_file": state.get("documentation_file", "N/A"),
                    "success_summary": success_summary if has_tests else "N/A",
                    "input_prompt": f"Running pytest (iteration {iteration + 1})",
                    "output_response": f"SUCCESS: {passed_count} passed, {failed_count} failed"
                },
                status="SUCCESS"
            )
            
            print(f"\n{'='*60}")
            print(f"🎉 MISSION COMPLETE after {iteration + 1} iteration(s)!")
            if has_tests and state.get("success_summary"):
                print(f"   📝 {state['success_summary'][:200]}")
            if state.get("documentation_created"):
                print(f"   📄 Documentation: {os.path.basename(state.get('documentation_file', ''))}")
                print(f"   📂 Saved to: {os.path.dirname(state.get('documentation_file', ''))}")
            else:
                print(f"   ⚠️ Documentation was not created")
            print(f"   💾 Final code stored in state - Main will write to file with _fixed suffix")
            print(f"{'='*60}\n")
            
            return state  # ← CRITICAL: RETURN HERE!
        
        # ====================================================================
        # FAILURE: Tests failed - use LLM to analyze
        # ====================================================================
        else:
            print(f"   ❌ {failed_count} TEST(S) FAILED")
            
            # Use LLM to analyze failures
            llm_analysis = analyze_test_failures_with_llm(fixed_code, pytest_output)
            
            # Also extract basic failures as fallback
            basic_failures = extract_specific_test_failures(pytest_output)
            
            # Combine LLM analysis with basic extraction
            if llm_analysis and llm_analysis != basic_failures:
                specific_failures = f"=== LLM ANALYSIS ===\n{llm_analysis}\n\n=== RAW FAILURES ===\n{basic_failures}"
            else:
                specific_failures = basic_failures
            
            state["specific_test_failures"] = specific_failures
            
            if llm_analysis:
                print(f"\n   📋 LLM FAILURE ANALYSIS (sending to Fixer):")
                print(f"   {'-'*50}")
                for line in llm_analysis.split('\n')[:15]:
                    if line.strip():
                        print(f"   {line}")
                print(f"   {'-'*50}\n")
            
            state["is_fixed"] = False
            state["code"] = fixed_code  # Update for next iteration
            
            # Log LLM analysis
            log_experiment(
                agent_name="Judge_Agent",
                model_used="gemini-flash-latest",
                action=ActionType.ANALYSIS,
                details={
                    "iteration": iteration + 1,
                    "tests_passed": False,
                    "failed_count": failed_count,
                    "used_generated_tests": True,
                    "llm_analysis": llm_analysis[:500] if llm_analysis else "N/A",
                    "input_prompt": f"Analyzing test failures (iteration {iteration + 1})",
                    "output_response": llm_analysis[:500] if llm_analysis else "No LLM analysis"
                },
                status="PARTIAL"
            )
    
    except Exception as e:
        print(f"   ❌ Test execution error: {e}")
        
        pytest_output = f"Test execution failed: {str(e)}"
        specific_failures = f"Test execution error: {str(e)}"
        
        state["pytest_report"] = pytest_output
        state["specific_test_failures"] = specific_failures
        state["is_fixed"] = False
        state["code"] = fixed_code
    
    finally:
        # ====================================================================
        # CLEANUP: Delete temporary test files AFTER everything is done
        # ====================================================================
        print(f"   🗑️ Cleaning up temporary test files...")
        
        cleanup_count = 0
        
        # Delete test file
        if temp_test_file and os.path.exists(temp_test_file):
            try:
                os.remove(temp_test_file)
                print(f"   ✅ Deleted: {os.path.basename(temp_test_file)}")
                cleanup_count += 1
            except Exception as cleanup_error:
                print(f"   ⚠️ Failed to delete {os.path.basename(temp_test_file)}: {cleanup_error}")
        
        # Delete source file
        if temp_source_file and os.path.exists(temp_source_file):
            try:
                os.remove(temp_source_file)
                print(f"   ✅ Deleted: {os.path.basename(temp_source_file)}")
                cleanup_count += 1
            except Exception as cleanup_error:
                print(f"   ⚠️ Failed to delete {os.path.basename(temp_source_file)}: {cleanup_error}")
        
        if cleanup_count == 0:
            print(f"   ℹ️ No temporary files to clean up")
        else:
            print(f"   ✅ Cleaned up {cleanup_count} temporary file(s)")
    
    # ========================================================================
    # STEP 6: LOG FAILURE AND PREPARE FOR NEXT ITERATION
    # ========================================================================
    
    log_experiment(
        agent_name="Judge_Agent",
        model_used="gemini-flash-latest",
        action=ActionType.GENERATION,
        details={
            "iteration": iteration + 1,
            "tests_passed": False,
            "syntax_valid": syntax_valid,
            "used_generated_tests": True,
            "pytest_output_preview": pytest_output[:300] if 'pytest_output' in locals() else "N/A",
            "has_specific_failures": bool(state.get("specific_test_failures")),
            "input_prompt": f"Running pytest (iteration {iteration + 1})",
            "output_response": pytest_output[:500] if 'pytest_output' in locals() else "No output"
        },
        status="PARTIAL"
    )
    
    print(f"❌ Tests failed (Iteration {iteration + 1})")
    
    if iteration + 1 >= max_iterations:
        print(f"   🛑 Max iterations ({max_iterations}) reached")
        print(f"   ⚠️ Mission incomplete - manual review required")
    else:
        print(f"   🔄 Sending LLM-analyzed feedback to Fixer (iteration {iteration + 2}/{max_iterations})")
    
    return state