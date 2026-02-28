# Messy Code - Documentation

**Status**: Production Ready - All Tests Passed  
**File**: `messy_code.py`

---

## Overview
This module provides a utility function for range validation. It is designed to determine if a specific numerical value falls within a strictly defined boundary, specifically between 0 and 100, excluding the endpoints.

---

## Functions

### `is_between_zero_and_hundred(number)`

**Description:**  
Evaluates whether a given number is strictly greater than 0 and strictly less than 100.

**Parameters:**
- `number` (float): The numerical value to check against the range.

**Returns:**
- `bool`: Returns `True` if the number is within the range (0, 100), otherwise returns `False`.

**Examples:**
python
>>> is_between_zero_and_hundred(50.5)
True

>>> is_between_zero_and_hundred(0)
False

>>> is_between_zero_and_hundred(100)
False

>>> is_between_zero_and_hundred(-5)
False


**Edge Cases:**
- **Boundary Values:** Inputting exactly `0` or `100` returns `False` because the comparison is exclusive.
- **Negative Numbers:** Any negative number will return `False`.
- **Large Numbers:** Any number equal to or greater than `100` will return `False`.
- **Invalid Types:** Passing non-numeric types (like a string or `None`) will result in a `TypeError` as the function performs mathematical comparisons.

---

## Summary

### Functions Included
- `is_between_zero_and_hundred`: Checks if a number is strictly between 0 and 100 (exclusive).

### Testing Status
✅ All functions tested and validated