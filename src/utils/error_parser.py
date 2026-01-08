import re
import os

def parse_pylint(raw_text):
    """Extracts and formats pylint errors in a readable way."""
    if not raw_text or not raw_text.strip():
        return "No linting errors found."
    
    cleaned_lines = []
    lines = raw_text.splitlines()
    
    for line in lines:
        # Look for error/warning/convention markers
        if any(marker in line for marker in [": E", ": W", ": C", ": R", ": F"]):
            # Use os.path.basename to handle both Unix and Windows paths
            if os.sep in line or '/' in line:
                # Extract just the filename and message
                parts = line.replace('\\', '/').split('/')
                msg = parts[-1] if parts else line
                cleaned_lines.append(msg)
            else:
                cleaned_lines.append(line)
    
    if cleaned_lines:
        return "Linting Issues Found:\n" + "\n".join(cleaned_lines)
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