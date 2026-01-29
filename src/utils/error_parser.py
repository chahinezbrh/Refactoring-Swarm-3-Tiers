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
    """Extracts the relevant failure information from pytest output."""
    if not raw_text:
        return "No test output received."
    
    if "passed" in raw_text.lower() and "failed" not in raw_text.lower():
        return "All tests passed."
    
    # Try to extract the FAILURES section
    failures_match = re.search(
        r'={3,}\s*FAILURES\s*={3,}(.*)(?:={3,}\s*short test summary|$)',
        raw_text,
        re.DOTALL | re.IGNORECASE
    )
    
    if failures_match:
        failure_text = failures_match.group(1).strip()
        # Limit output size to prevent token overflow
        if len(failure_text) > 2000:
            failure_text = failure_text[:2000] + "\n\n... (output truncated)"
        return "Test Failures:\n" + failure_text
    
    # Try to extract the short test summary
    summary_match = re.search(
        r'={3,}\s*short test summary.*?={3,}(.*?)(?:={3,}|$)',
        raw_text,
        re.DOTALL | re.IGNORECASE
    )
    
    if summary_match:
        return "Test Summary:\n" + summary_match.group(1).strip()
    
    # Fallback: return last 1000 characters
    return "Test Output (last 1000 chars):\n" + raw_text[-1000:]