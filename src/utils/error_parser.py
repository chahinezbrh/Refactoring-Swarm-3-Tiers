import re

def parse_pylint(raw_text):
   
    if not raw_text.strip():
        return "No linting errors found."
    
    # We look for patterns like: path/to/file.py:12:0: E0602: Undefined variable
    cleaned_lines = []
    lines = raw_text.splitlines()
    for line in lines:
        if any(marker in line for marker in [": E", ": W", ": C"]): # Errors, Warnings, Convention
            # Remove the long file path to save tokens
            msg = line.split('/')[-1] if '/' in line else line
            cleaned_lines.append(msg)
            
    return "\n".join(cleaned_lines) if cleaned_lines else "Code quality is good."


def parse_pytest(raw_text):
    """Extracts only the Failures and Tracebacks from Pytest."""
    if "FAILURES" not in raw_text and "ERRORS" not in raw_text:
        return "All tests passed."

    # Find the section between 'FAILURES' and the summary at the end
    match = re.search(r'(_+ FAILURES _+)(.*)(_+ short test summary info _+)', raw_text, re.DOTALL)
    if match:
        return match.group(2).strip()
    
    return raw_text