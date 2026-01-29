import subprocess
import os
import sys
from src.utils.code_validator import get_safe_path, validate_syntax, is_safe_code, SANDBOX_DIR
from src.utils.error_parser import parse_pylint, parse_pytest


def read_file(filename):
    """Reads a code file from the sandbox and returns its content as a string."""
    try:
        path = get_safe_path(filename)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File '{filename}' not found in sandbox."
    except PermissionError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


def write_file(filename, content):
    """
    Writes the fixed code to a NEW file (filename_fixed.py) 
    inside the sandbox to avoid overwriting the original.
    """
    try:
        # 1. Generate the new filename (e.g., test.py -> test_fixed.py)
        name_part, extension_part = os.path.splitext(filename)
        new_filename = f"{name_part}_fixed{extension_part}"
        
        # 2. Get the safe path for the NEW filename
        path = get_safe_path(new_filename)
        
        # 3. Security: Check for dangerous code
        is_safe, msg = is_safe_code(content)
        if not is_safe: 
            return f"SECURITY ERROR: {msg}"
        
        # 4. Reliability: Check for syntax errors before saving
        is_valid, msg = validate_syntax(content)
        if not is_valid: 
            return f"SYNTAX ERROR: {msg}"
        
        # 5. Save the content to the new file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return f"SUCCESS: Fixed code saved as '{new_filename}'."
        
    except PermissionError as e:
        return f"PERMISSION ERROR: {str(e)}"
    except Exception as e:
        return f"ERROR: Failed to write file - {str(e)}"


def run_pylint(filename):
    """Runs pylint and returns a readable report."""
    try:
        path = get_safe_path(filename)

        if not os.path.exists(path):
            return f"Error: File '{filename}' not found in sandbox."

        result = subprocess.run(
            [sys.executable, "-m", "pylint", "--disable=all", "--enable=E,W", path],
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout + result.stderr

        if not output.strip():
            return "No linting issues detected."

        return parse_pylint(output)

    except subprocess.TimeoutExpired:
        return "Error: Pylint timed out (over 30 seconds)."
    except FileNotFoundError:
        return "Error: Pylint not installed. Run 'pip install pylint'."
    except Exception as e:
        return f"Error running Pylint: {str(e)}"


def run_pytest():
    """Runs pytest on all test files in the sandbox directory."""
    try:
        # Get the project root (2 levels up from src/utils/)
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_file_dir, '../..'))
        
        # Set up environment to include project root in Python path
        env = os.environ.copy()
        env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")

        # Check if sandbox directory exists
        if not os.path.exists(SANDBOX_DIR):
            return f"Error: Sandbox directory '{SANDBOX_DIR}' does not exist."

        # Run pytest
        result = subprocess.run(
            ["python", "-m", "pytest", SANDBOX_DIR, "-v"],
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        
        if result.returncode == 0:
            return "SUCCESS: All tests passed."
        else:
            return parse_pytest(result.stdout)
            
    except subprocess.TimeoutExpired:
        return "Error: Tests timed out (took longer than 30 seconds)."
    except FileNotFoundError:
        return "Error: Pytest not installed. Run 'pip install pytest' first."
    except Exception as e:
        return f"Error running Pytest: {str(e)}"