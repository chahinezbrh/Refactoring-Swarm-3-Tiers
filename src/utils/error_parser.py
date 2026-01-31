import re
import os

def parse_pylint(raw_text):
    """Extracts and formats pylint errors in a readable way."""
    if not raw_text or not raw_text.strip():
        return "No linting errors found."

    cleaned_lines = []
    lines = raw_text.splitlines()

    for line in lines:
        # Look for lines containing pylint codes: E, W, C, R, F
        if re.search(r'[EWCRF]\d{4}', line):
            # Extract just filename and message
            parts = line.split(':')
            if len(parts) >= 4:
                filename = os.path.basename(parts[0])
                rest = ':'.join(parts[1:])
                cleaned_lines.append(f"{filename}:{rest.strip()}")
            else:
                cleaned_lines.append(line.strip())

    if cleaned_lines:
        return "Linting Issues Found:\n" + "\n".join(cleaned_lines)
    else:
        # Check for default pylint message indicating no issues
        if "rated at 10" in raw_text or "Your code has been rated" in raw_text:
            return "Code quality is good."
        # Fallback: return raw output if short
        if 0 < len(raw_text.strip()) < 1000:
            return f"Pylint output (unparsed):\n{raw_text.strip()}"
        return "Code quality is good."


def parse_pytest(raw_text):
    """Extracts only the Failures and Tracebacks from Pytest output."""
    if not raw_text:
        return "No test output received."

    if "passed" in raw_text.lower() and "failed" not in raw_text.lower():
        return "All tests passed."

    # Extract FAILURES section
    failures_match = re.search(
        r'={3,}\s*FAILURES\s*={3,}(.*?)(?:={3,}\s*short test summary|$)',
        raw_text,
        re.DOTALL | re.IGNORECASE
    )
    if failures_match:
        failure_text = failures_match.group(1).strip()
        if len(failure_text) > 2000:
            failure_text = failure_text[:2000] + "\n\n... (output truncated)"
        return "Test Failures:\n" + failure_text

    # Extract short test summary
    summary_match = re.search(
        r'={3,}\s*short test summary.*?={3,}(.*?)(?:={3,}|$)',
        raw_text,
        re.DOTALL | re.IGNORECASE
    )
    if summary_match:
        return "Test Summary:\n" + summary_match.group(1).strip()

    # Fallback: return last 1000 characters
    return "Test Output (last 1000 chars):\n" + raw_text[-1000:]
