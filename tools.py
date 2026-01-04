import subprocess
from src.utils.code_validator import get_safe_path, validate_syntax, is_safe_code
from src.utils.error_parser import parse_pylint, parse_pytest

#function to read the code file and return it as a string
def read_file(filename):
 
    try:
        path = get_safe_path(filename)
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}"


#function that writes the fixed code in a file inside sandbox
def write_file(filename, content):
   
    try:
        path = get_safe_path(filename)
        
        #Check for dangerous code
        is_safe, msg = is_safe_code(content)
        if not is_safe: return msg
        
        #Check for syntax errors before saving
        is_valid, msg = validate_syntax(content)
        if not is_valid: return f"Refused to save: {msg}"
        
        with open(path, 'w') as f:
            f.write(content)
        return f"File {filename} saved successfully."
    except Exception as e:
        return f"Error: {str(e)}"

#function that returns syntax errors (caught from terminal)
def run_pylint(filename):
    """Runs linting and returns a cleaned, readable report for the Auditor."""
    try:
        path = get_safe_path(filename)
        # --msg-template formats it nicely for our parser
        result = subprocess.run(["pylint", path], capture_output=True, text=True)
        return parse_pylint(result.stdout)
    except Exception as e:
        return f"Error running Pylint: {str(e)}"


def run_pytest():
    """Runs tests and returns only the necessary failure details for the Judge."""
    try:
        # Import SANDBOX_DIR from validator
        from utils.code_validator import SANDBOX_DIR
        result = subprocess.run(["pytest", SANDBOX_DIR], capture_output=True, text=True, timeout=20)
        
        if result.returncode == 0:
            return "SUCCESS: All tests passed."
        else:
            return parse_pytest(result.stdout)
    except subprocess.TimeoutExpired:
        return "ERROR: Tests timed out (possible infinite loop)."
    except Exception as e:
        return f"Error running Pytest: {str(e)}"