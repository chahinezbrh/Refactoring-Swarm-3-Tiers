"""
FIXER Agent: Applies corrections to code based on refactoring plan

Responsibilities:
1. Read refactoring plan from Auditor (iteration 1)
2. Read test failures from Judge (iteration 2+)
3. Generate fixed code using LLM
4. Extract code from LLM response
5. Validate syntax
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from src.utils.logger import log_experiment, ActionType
from src.prompts.fixer_prompts import FIXER_PROMPT
import os
import re


def extract_code_from_response(response: str) -> str:
    """
    Extract Python code from LLM response
    
    LLMs often return code with explanations like:
    "Here's the fixed code:
    ```python
    def foo():
        pass
    ```
    This fixes the issue by..."
    
    This function extracts ONLY the code part.
    
    Methods (in order):
    1. Find ```python blocks
    2. Detect code start (import, def, class)
    3. Fallback: Clean and return all
    
    Args:
        response: Raw LLM response
        
    Returns:
        Extracted Python code
    """
    if isinstance(response, list):
        response = ' '.join(str(x) for x in response)
    
    response = str(response).strip()
    
    # ====================================================================
    # METHOD 1: Extract from ```python blocks (most reliable)
    # ====================================================================
    python_blocks = re.findall(
        r'```(?:python)?\s*\n(.*?)```', 
        response, 
        re.DOTALL | re.IGNORECASE
    )
    
    if python_blocks:
        # Take the LARGEST block (usually the complete code)
        code = max(python_blocks, key=len).strip()
        code = code.rstrip('`').strip()
        return code
    
    # ====================================================================
    # METHOD 2: Detect code start and extract
    # ====================================================================
    lines = response.split('\n')
    code_lines = []
    in_code = False
    
    for line in lines:
        stripped = line.strip()
        
        # Skip explanatory phrases at start
        if not in_code and any(phrase in stripped.lower() for phrase in [
            'here is', 'this is', 'i have', 'the following',
            "here's", 'below is', 'the fixed', 'corrected'
        ]):
            continue
        
        # Detect code start
        if any(stripped.startswith(x) for x in [
            '"""', "'''", 'import ', 'from ', 'def ', 'class ', '#'
        ]):
            in_code = True
        
        # Stop at explanatory text after code
        if in_code and any(phrase in stripped.lower() for phrase in [
            'explanation:', 'note:', 'key changes:', 'summary:',
            'this implementation', 'the code above', 'i have fixed',
            'changes made:', 'what i did:'
        ]):
            break
        
        if in_code:
            code_lines.append(line)
    
    if code_lines:
        code = '\n'.join(code_lines).strip()
        # Remove trailing markdown
        code = re.sub(r'```.*$', '', code, flags=re.MULTILINE | re.DOTALL)
        return code.strip()
    
    # ====================================================================
    # FALLBACK: Return everything but clean it
    # ====================================================================
    cleaned = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
    return cleaned.strip()


def validate_code_syntax(code: str) -> tuple[bool, str]:
    """
    Validate Python syntax by attempting to compile
    
    Args:
        code: Python code string
        
    Returns:
        (is_valid, error_message)
    """
    try:
        compile(code, '<string>', 'exec')
        return True, ""
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def fixer_agent(state: dict) -> dict:
    """
    FIXER Agent: Applies corrections based on feedback
    
    Workflow:
    1. Build prompt (refactoring plan OR test failures)
    2. Call LLM to generate fixed code
    3. Extract code from response
    4. Validate syntax
    5. Update state
    
    Args:
        state: Workflow state containing:
            - code: Current code (buggy or from previous iteration)
            - refactoring_plan: Plan from Auditor
            - iteration_count: Current iteration
            - pytest_report: Test results (if iteration > 0)
            - specific_test_failures: Extracted failures (if iteration > 0)
        
    Returns:
        Updated state with:
            - fixed_code: Code after applying fixes
    """
    print("🔧 [FIXER] Applying fixes...")
    
    buggy_code = state["code"]
    refactoring_plan = state.get("refactoring_plan", "")
    iteration = state.get("iteration_count", 0)
    file_name = state.get("file_name", "unknown.py")
    
    # ========================================================================
    # STEP 1: Build Context-Aware Prompt
    # ========================================================================
    
    if iteration > 0:
        # ====================================================================
        # ITERATION 2+: Use test failures from Judge
        # ====================================================================
        pytest_report = state.get("pytest_report", "")
        specific_failures = state.get("specific_test_failures", "")
        
        # Prioritize specific failures
        if specific_failures:
            error_context = specific_failures
            print(f"   📋 Using specific test failures from Judge")
        elif pytest_report and "FAILED" in pytest_report:
            error_context = pytest_report[-800:] if len(pytest_report) > 800 else pytest_report
            print(f"   📋 Using pytest output from Judge")
        else:
            error_context = "Tests failed but no specific error details available"
        
        # Build enhanced prompt
        enhanced_prompt = f"""⚠️ ITERATION {iteration + 1} - TESTS ARE FAILING!

The Judge executed tests and they FAILED. You must fix the EXACT issues reported.

SPECIFIC TEST FAILURES FROM JUDGE:
{'='*60}
{error_context}
{'='*60}

Read the failure messages CAREFULLY:
- What the test EXPECTED (correct behavior)
- What your code ACTUALLY returned (the bug)
- The exact assertion that failed

ORIGINAL REFACTORING PLAN FROM AUDITOR:
{refactoring_plan[:1000] if len(refactoring_plan) > 1000 else refactoring_plan}

CURRENT CODE THAT FAILED TESTS:
```python
{buggy_code}
```

CRITICAL REQUIREMENTS:
1. Address the EXACT issues shown in test failures
2. Pay attention to expected vs actual values
3. Return appropriate default values for edge cases
4. Add error handling where needed
5. Ensure proper Python syntax
6. Keep function signatures unchanged
7. Don't add new functionality - only fix bugs

OUTPUT FORMAT - EXTREMELY IMPORTANT:
- Return ONLY valid Python code
- NO markdown formatting (no ``` or ```python)
- NO explanations or comments about changes
- Start directly with imports or docstring
- End when code is complete

Fixed code:"""
        
        input_prompt = enhanced_prompt
        
    else:
        # ====================================================================
        # ITERATION 1: Use refactoring plan from Auditor
        # ====================================================================
        input_prompt = FIXER_PROMPT.format(
            code=buggy_code,
            refactoring_plan=refactoring_plan
        )
        print(f"   📋 Using refactoring plan from Auditor")
    
    # ========================================================================
    # STEP 2: Call LLM to Generate Fixed Code
    # ========================================================================
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        temperature=0.1,  # Low but not 0 - allows slight creativity
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        max_retries=1
    )
    
    try:
        print("   🤖 Calling LLM to generate fixes...")
        response = llm.invoke(input_prompt)
        
        # Handle list or string response
        if isinstance(response.content, list):
            output_response = ' '.join(str(item) for item in response.content)
        else:
            output_response = str(response.content)
        
        print(f"   📥 Received {len(output_response)} characters from LLM")
        
        # ====================================================================
        # STEP 3: Extract Code from Response
        # ====================================================================
        
        fixed_code = extract_code_from_response(output_response)
        
        # Validate extraction
        if len(fixed_code) < 50:
            print(f"   ⚠️ Code extraction failed - only {len(fixed_code)} chars")
            raise ValueError(f"Code extraction too short: {len(fixed_code)} characters")
        
        print(f"   ✅ Extracted {len(fixed_code)} characters of code")
        
        # ====================================================================
        # STEP 4: Validate Syntax
        # ====================================================================
        
        validation_passed, validation_error = validate_code_syntax(fixed_code)
        
        if validation_passed:
            print(f"   ✅ Syntax validation PASSED")
        else:
            print(f"   ❌ Syntax validation FAILED: {validation_error}")
            
            # Show problematic line if available
            if "Line" in validation_error:
                try:
                    line_num = int(re.search(r'Line (\d+)', validation_error).group(1))
                    lines = fixed_code.split('\n')
                    if 0 <= line_num - 1 < len(lines):
                        print(f"      >>> Line {line_num}: {lines[line_num - 1]}")
                except:
                    pass
        
        # ====================================================================
        # STEP 5: Log the Attempt
        # ====================================================================
        
        log_experiment(
            agent_name="Fixer_Agent",
            model_used="gemini-flash-latest",
            action=ActionType.FIX,
            details={
                "file_name": file_name,
                "input_prompt": input_prompt[:500] + "..." if len(input_prompt) > 500 else input_prompt,
                "output_response": output_response[:500] + "..." if len(output_response) > 500 else output_response,
                "iteration": iteration,
                "original_code_length": len(buggy_code),
                "fixed_code_length": len(fixed_code),
                "validation_passed": validation_passed,
                "validation_error": validation_error if not validation_passed else None,
            },
            status="SUCCESS" if validation_passed else "PARTIAL"
        )
        
        # ====================================================================
        # STEP 6: Update State
        # ====================================================================
        
        state["fixed_code"] = fixed_code
        
        # Build status message
        status_parts = []
        if validation_passed:
            status_parts.append("Syntax ✅")
        else:
            status_parts.append("Syntax ❌")
        
        state["messages"].append({
            "role": "fixer",
            "content": f"Iteration {iteration + 1}: {', '.join(status_parts)}"
        })
        
        print(f"   ✅ Fix attempt complete")
        
    except Exception as e:
        print(f"   ❌ Fixer error: {e}")
        
        log_experiment(
            agent_name="Fixer_Agent",
            model_used="gemini-flash-latest",
            action=ActionType.FIX,
            details={
                "file_name": file_name,
                "input_prompt": input_prompt[:500] + "..." if 'input_prompt' in locals() else "N/A",
                "output_response": f"ERROR: {str(e)}",
                "error_message": str(e),
                "iteration": iteration
            },
            status="FAILURE"
        )
        
        # Don't break workflow - keep previous code
        state["fixed_code"] = buggy_code
        state["messages"].append({
            "role": "fixer",
            "content": f"Iteration {iteration + 1}: Error - {str(e)[:100]}"
        })
    
    return state