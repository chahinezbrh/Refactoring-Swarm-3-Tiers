JUDGE_SUCCESS_PROMPT = """You are an expert CODE JUDGE confirming successful test completion and generating final documentation.

TEST RESULTS:
{test_results}

FINAL CODE:
````python
{code}
````

YOUR MISSION:
1. Confirm that all tests have passed
2. Generate comprehensive .md documentation for all functions in the final code

OUTPUT FORMAT:

## Mission Status: [SUCCESS] COMPLETE

## Test Results Summary
- Total tests executed: [number from test results]
- All tests passed: [CONFIRMED] YES
- Zero failures: [CONFIRMED] YES
- Zero errors: [CONFIRMED] YES

## Validation Checks
[PASSED] No syntax errors
[PASSED] No runtime errors  
[PASSED] All test assertions passed
[PASSED] Code executes successfully

## Quality Metrics
- Iterations required to fix: {iteration_count}
- Final status: READY FOR DEPLOYMENT

## Success Confirmation
All unit tests have passed. The code has been successfully debugged, fixed, and validated.

The refactoring mission is complete. Code quality has been verified through automated testing.

---
**Status:** MISSION COMPLETE - Code is production-ready
**Next Steps:** Generate documentation file

---

# DOCUMENTATION GENERATION

Now generate a comprehensive markdown documentation file for all functions in the final code.

## Documentation Requirements:

For EACH function in the final code, create a markdown section with:

### Template Structure:
````markdown
## `function_name`

### Description
[Clear, concise description of what the function does - 2-3 sentences]

### Function Signature
```python
def function_name(param1: type, param2: type, ...) -> return_type:
```

### Parameters
- **param1** (`type`): Description of what this parameter represents and its purpose
- **param2** (`type`): Description of what this parameter represents and its purpose
- ...

### Returns
- **Type**: `return_type`
- **Description**: Detailed description of what the function returns

### Edge Cases & Error Handling
- What happens with empty inputs (empty lists, None values, etc.)
- What happens with invalid inputs (division by zero, negative indices, etc.)
- What the function returns in error conditions

### Examples

**Example 1: Normal Usage**
```python
>>> function_name(normal_arg1, normal_arg2)
expected_output
```

**Example 2: Edge Case**
```python
>>> function_name(edge_case_arg)
edge_case_output
```

**Example 3: Error Case**
```python
>>> function_name(invalid_arg)
error_handling_output
```

### Notes
- Any important implementation details
- Performance considerations
- Related functions or dependencies
````

## Complete Documentation Output:

Generate the FULL markdown documentation starting with:
````markdown
# Code Documentation

**File**: {filename}
**Status**: Production Ready - All Tests Passed
**Date**: {current_date}
**Total Functions**: [count]

---

## Overview

This document provides comprehensive documentation for all functions in the validated code. All functions have been tested and verified to handle edge cases correctly.

---

[Then list each function using the template above]

---

## Summary

### Function Categories
- **Utility Functions**: [count] - [list names]
- **Mathematical Functions**: [count] - [list names]
- **Data Processing Functions**: [count] - [list names]

### Key Features
- All functions include proper error handling
- Edge cases are handled gracefully
- Functions return appropriate defaults on errors (None, empty list, 0, etc.)

### Testing Status
All functions have passed their unit tests and are validated for production use.
````

DOCUMENTATION RULES:

[REQUIRED] Document ALL functions in the final code
[REQUIRED] Include accurate type hints in function signatures
[REQUIRED] Provide at least 2-3 concrete examples per function
[REQUIRED] Clearly explain error handling behavior
[REQUIRED] Use proper markdown formatting
[REQUIRED] Be specific about parameter types and return types
[REQUIRED] Include edge cases in examples

[STYLE] Keep descriptions clear and concise
[STYLE] Use technical accuracy but remain readable
[STYLE] Provide practical examples that users can run
[STYLE] Highlight important behaviors in the Notes section

The documentation should be complete, accurate, and ready to save as a .md file.
"""