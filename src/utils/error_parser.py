import re
import os







def parse_pylint(raw_text):
    """Extracts and formats pylint errors in a readable way."""
    if not raw_text or not raw_text.strip():
        return "No linting errors found."
    
    cleaned_lines = []
    lines = raw_text.splitlines()
    
    for line in lines:
        # Pylint format: filename.py:line:col: CODE: message
        # Look for lines with error codes like E0602, W0611, C0103, etc.
        # Pattern matches: E0602, W0611, C0103, R1705, F0401, etc.
        if re.search(r'[EWCRF]\d{4}', line):
            # This line contains a pylint issue code
            # Extract just the relevant part (remove full path if present)
            if os.sep in line or '/' in line:
                # Try to extract just filename and message
                parts = line.split(':')
                if len(parts) >= 4:
                    # Format: path:line:col: CODE: message
                    filename = os.path.basename(parts[0])
                    rest = ':'.join(parts[1:])
                    cleaned_lines.append(f"{filename}:{rest}")
                else:
                    cleaned_lines.append(line.strip())
            else:
                cleaned_lines.append(line.strip())
    
    if cleaned_lines:
        return "Linting Issues Found:\n" + "\n".join(cleaned_lines)
    else:
        # Check if the output indicates no issues
        if "rated at 10" in raw_text or "Your code has been rated" in raw_text:
            return "Code quality is good."
        # If we got output but couldn't parse it, show raw output for debugging
        if len(raw_text.strip()) > 0 and len(raw_text) < 1000:
            return f"Pylint output (could not parse standard format):\n{raw_text.strip()}"
        else:
            return "Code quality is good."


def parse_pytest(raw_text):
    """
    Extracts relevant failure information while PRESERVING the summary line
    so the Judge Agent can count passed/failed tests.
    """
    if not raw_text:
        return "No test output received."

    # 1. Extract the Summary Line (e.g., "2 passed, 1 failed in 0.05s")
    # We look for the line at the end of the output surrounded by '=' or just the stats.
    summary_line = ""
    summary_match = re.search(r'(=+\s+(?:\d+\s+\w+,\s*)*\d+\s+\w+\s+in\s+[\d\.]+s\s+=+)', raw_text)
    if summary_match:
        summary_line = summary_match.group(1)
    else:
        # Fallback: catch common short summary patterns
        last_lines = raw_text.strip().split('\n')
        for line in reversed(last_lines):
            if any(word in line for word in ["passed", "failed", "error", "skipped"]):
                summary_line = line
                break

    # 2. Case: All Tests Passed
    if "passed" in raw_text.lower() and "failed" not in raw_text.lower() and "error" not in raw_text.lower():
        return f"SUCCESS: All tests passed.\nSummary: {summary_line if summary_line else 'All tests passed'}"

    # 3. Case: Failures detected - Extract "FAILURES" section
    failures_match = re.search(
        r'={3,}\s*FAILURES\s*={3,}(.*)(?:={3,}\s*short test summary|$)',
        raw_text,
        re.DOTALL | re.IGNORECASE
    )
    
    parsed_output = ""
    if failures_match:
        failure_text = failures_match.group(1).strip()
        # Limit size to prevent token overflow while keeping relevant data
        if len(failure_text) > 1500:
            failure_text = failure_text[:1500] + "\n\n... (detailed output truncated)"
        parsed_output = f"Test Failures Found:\n{failure_text}"
    else:
        # 4. Fallback for Collection Errors or Import Errors
        # If pytest crashed before running tests, extract the end of the output
        parsed_output = "Pytest encountered an error (likely collection or import error):\n" + raw_text[-1000:]

    # CRITICAL: Always append the summary_line at the very end.
    # The Judge Agent uses Regex on the final string to count successes.
    return f"{parsed_output}\n\nRESULT_SUMMARY: {summary_line}"