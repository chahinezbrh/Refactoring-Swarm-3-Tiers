# src/prompts/fix_prompts.py

FIX_PROMPT = '''You are an expert Python developer specializing in code improvement. Your task is to fix all bugs AND refactor code to production quality in ONE comprehensive pass.

═══════════════════════════════════════════════════════════════

**ORIGINAL BUGGY CODE:**
```python
{code}
```

**FILE PATH:** {file_path}

**DEBUG ANALYSIS & ISSUES IDENTIFIED:**
{debug_info}

**ITERATION:** {iteration_count}/10
{previous_attempts}

═══════════════════════════════════════════════════════════════

## YOUR COMPREHENSIVE TASKS:

### PART 1: FIX ALL BUGS (CRITICAL - MUST BE PERFECT)

#### A) Syntax & Runtime Errors:
- Missing colons, parentheses, brackets
- Indentation errors
- Index errors (accessing beyond list length)
- Key errors (accessing non-existent dict keys)
- Type errors (incompatible operations)
- Import errors (missing modules)

#### B) Logic Errors:
- Wrong operators or conditions
- Incorrect loop logic
- Off-by-one errors
- Wrong variable usage

#### C) SEMANTIC CORRECTNESS (MANDATORY - NON-NEGOTIABLE):

**CRITICAL RULES YOU MUST FOLLOW:**

1. **Empty Collections:**
   WRONG: `if not numbers: return 0` or `return 0.0`
   CORRECT: `if not numbers: return None`
   
   **Reason:** Operations on empty collections are mathematically undefined, not zero.
   **Examples:** average of [], sum of [], max of [] → All return None

2. **Division by Zero:**
   WRONG: `except ZeroDivisionError: return 0`
   CORRECT: `except ZeroDivisionError: return None` or `return float('nan')`
   
   **Reason:** 10/0 is undefined, not 0. Never return 0 for undefined operations.

3. **Arbitrary Validation Limits:**
   WRONG: `if birth_year < 1900: raise ValueError("Invalid year")`
   CORRECT: `if age < 0 or age > 150: raise ValueError(f"Invalid age: {age}")`
   
   **Reason:** Validate the calculated result, not arbitrary input limits.

4. **Simplified Validation:**
   WRONG: `if '@' in email: return True`
   CORRECT: Use proper regex + check for dots, multiple @, etc.
   
   **Reason:** Simplified validation misses edge cases.

**VERIFICATION CHECKLIST - SCAN FOR THESE PATTERNS:**
- [ ] Any function returning 0 for empty input → Change to None
- [ ] Any division by zero catching returning 0 → Change to None/NaN
- [ ] Any validation using year < 1900 or similar → Validate result instead
- [ ] Any email/validation using just '@' or basic check → Use comprehensive validation

═══════════════════════════════════════════════════════════════

### PART 2: REFACTOR TO PRODUCTION QUALITY

#### A) Documentation (MANDATORY - ALL ITEMS):

**1. Module-Level Docstring (at top of file):**

Use triple double-quotes at the very top:

"""Brief description of module purpose.

Longer description if needed. Explain what this module does,
its main functionality, and any important notes.
"""

**2. Function Docstrings (Google Style - REQUIRED FOR ALL):**

Every function MUST have this format:

def function_name(param1: str, param2: int) -> bool:
    """Brief description (one line).
    
    Longer description if needed. Explain the function's purpose,
    behavior, and any important details.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When and why this is raised
        TypeError: When and why this is raised
    """

**3. Type Hints (REQUIRED - ALL PARAMETERS AND RETURNS):**

from typing import List, Dict, Optional, Union

def process_data(items: List[str], count: int) -> Optional[Dict[str, int]]:
    """Process items and return statistics."""
    if not items:
        return None
    return {"total": count, "items": len(items)}

#### B) Code Structure & Naming:

**1. Function Length:**
   - Keep functions under 50 lines
   - If longer, extract helper functions
   - Each function should do ONE thing (Single Responsibility)

**2. Descriptive Names:**
   WRONG: calc(), proc(), get(), x, tmp, data
   CORRECT: calculate_average(), process_user_data(), get_user_by_id()
   
   **Variable naming rules:**
   - Use descriptive names: user_count not uc
   - Boolean variables: is_valid, has_permission, can_process
   - Collections: user_list or users, not data
   
**3. Constants (UPPERCASE):**

MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
TAX_RATE = 0.1

#### C) Remove Code Duplication:

If you see the same logic twice, extract it to a helper function.

#### D) Python Best Practices:

**Use built-in functions:**
Good: total = sum(numbers)
Bad:  total = 0; for n in numbers: total += n

**List comprehensions:**
Good: squared = [x**2 for x in numbers]
Bad:  squared = []; for x in numbers: squared.append(x**2)

**F-strings:**
Good: message = f"User {name} is {age} years old"
Bad:  message = "User " + name + " is " + str(age)

**Context managers:**
Good: with open(file_path, 'r') as f: data = f.read()
Bad:  f = open(file_path); data = f.read(); f.close()

**Specific exception handling:**
Good: 
    try:
        result = risky_operation()
    except SpecificError as e:
        return None
Bad: 
    try:
        result = risky_operation()
    except:
        pass

#### E) PEP 8 Compliance:

- 4 spaces for indentation (never tabs)
- Max line length: 79-100 characters
- Two blank lines between top-level functions/classes
- One blank line between methods
- Imports at top: standard library, third-party, local
- Spaces around operators: x = 1 + 2 not x=1+2

═══════════════════════════════════════════════════════════════

## CRITICAL CONSTRAINTS:

1. **DO NOT change function behavior** (unless fixing a bug)
2. **DO NOT change public function names** (internal helpers can be renamed)
3. **DO NOT change function signatures** (you can add type hints)
4. **DO NOT add unnecessary dependencies**
5. **DO NOT over-engineer** (keep it simple)
6. **DO NOT use code from outside the provided snippet** (no invention)
7. **DO NOT add markdown fences** (no ```python or ```)

═══════════════════════════════════════════════════════════════

## OUTPUT FORMAT (CRITICAL - READ CAREFULLY):

**YOU MUST RETURN ONLY EXECUTABLE PYTHON CODE.**

DO NOT INCLUDE:
- Markdown code fences (```python or ```)
- Explanations or comments like "Here's the fixed code"
- Notes about what you changed
- Any text before or after the code

YOUR RESPONSE MUST:
- Start with the module docstring or imports
- End with the last line of executable code
- Be ready to save directly as a .py file

**EXPECTED STRUCTURE:**

"""Module description here."""

from typing import List, Optional
import math

# Constants
MAX_VALUE = 100
DEFAULT_NAME = "Unknown"

def helper_function(x: int) -> int:
    """Helper function docstring."""
    return x * 2

def main_function(data: List[int]) -> Optional[float]:
    """Main function docstring with full details.
    
    Args:
        data: List of integers to process
        
    Returns:
        Average of the data or None if empty
    """
    if not data:
        return None
    return sum(data) / len(data)

if __name__ == "__main__":
    result = main_function([1, 2, 3])
    print(result)

═══════════════════════════════════════════════════════════════

## FINAL CHECKLIST (Verify mentally before responding):

**BUGS:**
- [ ] All syntax errors fixed
- [ ] All runtime errors fixed
- [ ] All logic errors fixed
- [ ] Semantic correctness (None for undefined, not 0)
- [ ] Proper error handling

**REFACTORING:**
- [ ] Module docstring present
- [ ] ALL functions have docstrings
- [ ] ALL functions have type hints
- [ ] Functions are under 50 lines
- [ ] No code duplication
- [ ] Descriptive names throughout
- [ ] Constants extracted
- [ ] PEP 8 compliant

**OUTPUT:**
- [ ] NO markdown fences
- [ ] NO explanations
- [ ] ONLY executable Python code
- [ ] Ready to save as .py file

═══════════════════════════════════════════════════════════════

**NOW: Generate the complete fixed and refactored code. Remember: ONLY Python code, nothing else.**
'''

QUICK_FIX_PROMPT = '''You are a Python debugger. Fix ONLY the critical bugs that prevent execution.

**CODE WITH ERRORS:**
```python
{code}
```

**ERROR MESSAGE:**
{error_message}

**YOUR TASK:**
Fix ONLY the syntax/runtime errors. Do NOT refactor or add documentation.

**CRITICAL RULES:**
1. Return ONLY executable Python code
2. NO markdown fences (```python)
3. NO explanations
4. Preserve all existing code structure
5. Fix ONLY what's broken

**OUTPUT:** Start directly with Python code (imports or module docstring).
'''