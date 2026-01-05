# src/prompts/generation_prompts.py

TEST_GENERATION_PROMPT = """You are a unit test expert. Generate comprehensive pytest tests for the following Python code.

**CODE TO TEST:**
```python
{code}
```

**FILE NAME:** {file_name}

**YOUR TASK:**
Generate a complete pytest test file that validates this code's functionality.

**TEST COVERAGE REQUIREMENTS:**
1. **Normal cases:** Test expected behavior with valid inputs
2. **Edge cases:** Test boundary conditions (empty lists, zero, None, etc.)
3. **Error cases:** Test that appropriate exceptions are raised for invalid inputs
4. **Integration:** If the code calls other functions, test the interactions

**OUTPUT FORMAT:**
Return ONLY executable Python/pytest code, no markdown fences, no explanations.

**EXAMPLE OUTPUT:**
import pytest
from {module_name} import function_to_test

def test_normal_case():
    result = function_to_test(valid_input)
    assert result == expected_output

def test_edge_case_empty_input():
    result = function_to_test([])
    assert result == []

def test_invalid_input_raises_exception():
    with pytest.raises(ValueError):
        function_to_test(invalid_input)

**CRITICAL:**
- Use descriptive test names (test_<scenario>)
- Include assertions with clear failure messages
- Cover at least 80% of code paths
"""

VALIDATION_PROMPT = """You are a code quality judge. Validate if the fixed code meets all requirements.

**ORIGINAL BUGGY CODE:**
```python
{original_code}
```

**FIXED CODE:**
```python
{fixed_code}
```

**BUGS THAT WERE SUPPOSED TO BE FIXED:**
{bug_list}

**TEST RESULTS:**
{test_results}

**PYLINT BEFORE:** {pylint_score_before}
**PYLINT AFTER:** {pylint_score_after}

**YOUR TASK:**
Determine if the fix is acceptable or if the code should go back to the Fixer.

**OUTPUT FORMAT (STRICT JSON):**
```json
{
  "verdict": "ACCEPT | REJECT | NEEDS_REFINEMENT",
  "all_bugs_fixed": true,
  "tests_passing": true,
  "quality_improved": true,
  "remaining_issues": [
    "List any bugs still present or new issues introduced"
  ],
  "feedback_for_fixer": "If REJECT/NEEDS_REFINEMENT, explain what's wrong",
  "confidence": "HIGH | MEDIUM | LOW"
}
```

**ACCEPTANCE CRITERIA:**
- ACCEPT: All bugs fixed + tests pass + quality improved
- NEEDS_REFINEMENT: Bugs fixed but quality degraded or minor issues
- REJECT: Critical bugs remain or new bugs introduced

**CRITICAL:** Return ONLY valid JSON, no markdown.
"""