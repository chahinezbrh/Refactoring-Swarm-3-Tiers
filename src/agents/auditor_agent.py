# src/agents/auditor_agent.py
import os
import sys
import tempfile
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from src.utils.logger import log_experiment, ActionType
from src.prompts.auditor_prompts import AUDITOR_PROMPT

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import run_pylint


def detect_generic_patterns(code: str) -> list:
    """
    Detect GENERIC bug patterns that apply to any Python code
    
    Returns list of potential issues found
    """
    issues = []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue
        
        # PATTERN 1: Division without zero check
        if '/' in line and '//' not in line and not line.strip().startswith('#'):
            context_start = max(0, i - 5)
            context_end = min(len(lines), i + 2)
            context = '\n'.join(lines[context_start:context_end])
            
            has_zero_check = any([
                '== 0' in context,
                '!= 0' in context,
                '> 0' in context,
                'if not' in context and any(var in context for var in ['denominator', 'divisor', 'count', 'total']),
            ])
            
            if not has_zero_check and 'try' not in context:
                issues.append({
                    'line': i,
                    'category': 'RUNTIME_ERROR',
                    'severity': 'CRITICAL',
                    'description': f'Division without zero check: `{stripped}`',
                    'fix': 'Add check: if denominator != 0: ... else: return None'
                })
        
        # PATTERN 2: List/array access without bounds check
        if '[' in line and ']' in line:
            if re.search(r'\w+\[\w+\]', line):
                context_start = max(0, i - 5)
                context_end = min(len(lines), i + 2)
                context = '\n'.join(lines[context_start:context_end])
                
                has_bounds_check = any([
                    'len(' in context,
                    '< len' in context,
                    'if ' in context and 'in ' in context,
                    'try' in context,
                    'IndexError' in context
                ])
                
                if not has_bounds_check:
                    issues.append({
                        'line': i,
                        'category': 'RUNTIME_ERROR',
                        'severity': 'HIGH',
                        'description': f'List access without bounds check: `{stripped}`',
                        'fix': 'Check: if index < len(list): ...'
                    })
        
        # PATTERN 3: Dictionary access without key check
        if re.search(r'\w+\[[\'\"]?\w+[\'\"]?\]', line) and 'list' not in line.lower():
            context_start = max(0, i - 5)
            context_end = min(len(lines), i + 2)
            context = '\n'.join(lines[context_start:context_end])
            
            has_key_check = any([
                'in ' in context and 'if' in context,
                '.get(' in context,
                'try' in context,
                'KeyError' in context
            ])
            
            if not has_key_check:
                issues.append({
                    'line': i,
                    'category': 'RUNTIME_ERROR',
                    'severity': 'HIGH',
                    'description': f'Dictionary access without key check: `{stripped}`',
                    'fix': 'Use .get() or check: if key in dict: ...'
                })
        
        # PATTERN 4: Empty collection operations
        if any(func in line for func in ['sum(', 'max(', 'min(', 'average(']):
            context_start = max(0, i - 5)
            context_end = min(len(lines), i + 2)
            context = '\n'.join(lines[context_start:context_end])
            
            has_empty_check = any([
                'if not' in context,
                'if len' in context,
            ])
            
            if not has_empty_check:
                issues.append({
                    'line': i,
                    'category': 'RUNTIME_ERROR',
                    'severity': 'HIGH',
                    'description': f'Aggregation function without empty check: `{stripped}`',
                    'fix': 'Check: if not collection: return default_value'
                })
        
        # PATTERN 5: Mutable default argument
        if 'def ' in line and '=' in line:
            if any(default in line for default in ['=[]', '={}', '=()', '= []', '= {}', '= ()']):
                issues.append({
                    'line': i,
                    'category': 'DATA_STRUCTURE',
                    'severity': 'HIGH',
                    'description': f'Mutable default argument: `{stripped}`',
                    'fix': 'Use: def func(arg=None): arg = arg or []'
                })
        
        # PATTERN 6: Infinite loop risk
        if 'while True:' in line:
            context_start = i
            context_end = min(len(lines), i + 20)
            context = '\n'.join(lines[context_start:context_end])
            
            has_exit = any([
                'break' in context,
                'return' in context,
                'raise' in context,
            ])
            
            if not has_exit:
                issues.append({
                    'line': i,
                    'category': 'LOGIC_ERROR',
                    'severity': 'CRITICAL',
                    'description': f'Potential infinite loop without exit: `{stripped}`',
                    'fix': 'Add break condition or return statement'
                })
    
    return issues


def auditor_agent(state: dict) -> dict:
    """
    AUDITOR Agent: Reads code, runs static analysis, produces refactoring plan
    
    Responsibilities:
    - Run Pylint static analysis
    - Detect generic bug patterns
    - Generate comprehensive audit report
    - Create refactoring plan for the Fixer
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with audit report and refactoring plan
    """
    print("🔍 [AUDITOR] Auditing code...")
    
    buggy_code = state["code"]
    file_name = state.get("file_name", "unknown.py")
    iteration = state.get("iteration_count", 0)
    
    if iteration > 0:
        print(f"   🔄 Re-auditing (iteration {iteration + 1})")
    
    # ===================================================================
    # STEP 1: Run Pylint (Static Analysis)
    # ===================================================================
    pylint_report = ""
    temp_file = None
    
    try:
        fd, temp_file = tempfile.mkstemp(suffix=".py", prefix="audit_")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(buggy_code)
        
        pylint_report = run_pylint(temp_file)
        print("   ✅ Pylint analysis complete")
        
    except Exception as e:
        pylint_report = f"Pylint skipped: {str(e)}"
        print(f"   ⚠️ Pylint skipped: {e}")
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
    
    # ===================================================================
    # STEP 2: Pattern Detection
    # ===================================================================
    print("   🔍 Running pattern detection...")
    pattern_issues = detect_generic_patterns(buggy_code)
    
    pattern_report = ""
    if pattern_issues:
        pattern_report = "\n🎯 PATTERN DETECTION FINDINGS:\n\n"
        
        # Group by category
        by_category = {}
        for issue in pattern_issues:
            category = issue.get('category', 'OTHER')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(issue)
        
        # Format output
        for category, issues in by_category.items():
            pattern_report += f"{category}:\n"
            for issue in issues:
                severity = issue.get('severity', 'MEDIUM')
                line = issue.get('line', 'N/A')
                desc = issue['description']
                fix = issue.get('fix', '')
                
                pattern_report += f"  [{severity}] Line {line}: {desc}\n"
                if fix:
                    pattern_report += f"           Fix: {fix}\n"
            pattern_report += "\n"
        
        print(f"   🎯 Found {len(pattern_issues)} pattern issues")
    
    # ===================================================================
    # STEP 3: Build Context from Previous Iterations
    # ===================================================================
    context_parts = []
    
    # Add pylint findings
    if pylint_report and "skipped" not in pylint_report.lower():
        context_parts.append(f"PYLINT STATIC ANALYSIS:\n{pylint_report}")
    
    # Add pattern detection findings
    if pattern_report:
        context_parts.append(pattern_report)
    
    # Add previous test failures if available
    if iteration > 0:
        pytest_report = state.get("pytest_report", "")
        specific_failures = state.get("specific_test_failures", "")
        
        if specific_failures:
            context_parts.append(f"SPECIFIC TEST FAILURES FROM PREVIOUS ITERATION:\n{specific_failures}")
        elif pytest_report and "FAILED" in pytest_report:
            context_parts.append(f"TEST FAILURES FROM PREVIOUS ITERATION:\n{pytest_report[:800]}")
    
    # Combine all context
    additional_context = "\n\n".join(context_parts) if context_parts else ""
    
    # ===================================================================
    # STEP 4: Generate Refactoring Plan with LLM
    # ===================================================================
    
    # Build prompt
    if additional_context:
        base_prompt = AUDITOR_PROMPT.replace("{code}", buggy_code)
        input_prompt = base_prompt + f"\n\nAUTOMATED ANALYSIS RESULTS:\n{additional_context}\n\nNow create a comprehensive refactoring plan that addresses all detected issues."
    else:
        input_prompt = AUDITOR_PROMPT.replace("{code}", buggy_code)
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        temperature=0,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        max_retries=1
    )
    
    try:
        response = llm.invoke(input_prompt)
        
        if isinstance(response.content, list):
            output_response = ' '.join(str(item) for item in response.content)
        else:
            output_response = str(response.content)
        
        # Combine all findings into refactoring plan
        refactoring_plan = ""
        if pattern_report:
            refactoring_plan += pattern_report + "\n\n"
        refactoring_plan += "REFACTORING PLAN:\n" + output_response
        
        # Log the audit
        log_experiment(
            agent_name="Auditor_Agent",
            model_used="gemini-flash-latest",
            action=ActionType.ANALYSIS,
            details={
                "file_analyzed": file_name,
                "input_prompt": input_prompt[:500] + "..." if len(input_prompt) > 500 else input_prompt,
                "output_response": output_response[:500] + "..." if len(output_response) > 500 else output_response,
                "code_length": len(buggy_code),
                "pylint_used": bool(pylint_report and "skipped" not in pylint_report.lower()),
                "pattern_issues_found": len(pattern_issues),
                "iteration": iteration
            },
            status="SUCCESS"
        )
        
        # Update state
        state["refactoring_plan"] = refactoring_plan
        state["pylint_report"] = pylint_report
        state["pattern_detection"] = pattern_report
        state["messages"].append({
            "role": "auditor",
            "content": f"Audit complete - {len(pattern_issues)} issues detected"
        })
        
        print(f"   ✅ Audit complete - refactoring plan generated")
        
    except Exception as e:
        log_experiment(
            agent_name="Auditor_Agent",
            model_used="gemini-flash-latest",
            action=ActionType.ANALYSIS,
            details={
                "input_prompt": input_prompt[:500] + "..." if len(input_prompt) > 500 else input_prompt,
                "output_response": f"ERROR: {str(e)}",
                "error_message": str(e),
                "iteration": iteration
            },
            status="FAILURE"
        )
        
        state["refactoring_plan"] = f"Error: {e}"
        state["pylint_report"] = ""
        print(f"   ❌ Audit failed: {e}")
    
    return state