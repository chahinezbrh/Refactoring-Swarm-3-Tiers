import subprocess
import os
from src.utils.code_validator import get_safe_path, validate_syntax, is_safe_code, SANDBOX_DIR
from src.utils.error_parser import parse_pylint, parse_pytest


def read_file(filename):
    """
    Reads a file and returns its contents as a string.
    
    Args:
        filename: Path to the file to read (relative to sandbox)
        
    Returns:
        File contents as string, or error message if reading fails
    """
    try:
        path = get_safe_path(filename)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


def run_pylint(filename):
    """
    Runs Pylint linting and returns a cleaned, readable report.
    
    ⚠️ SPECIAL HANDLING: This function accepts paths that may be outside 
    the sandbox (like temp files from analysis_agent), since Pylint only 
    reads files and doesn't execute them.
    
    Args:
        filename: Path to the Python file to lint (can be absolute path)
        
    Returns:
        Parsed Pylint report as string
    """
    try:
        # ✅ Check if file exists and is accessible
        if not os.path.exists(filename):
            return f"Error running Pylint: File not found: {filename}"
        
        if not os.path.isfile(filename):
            return f"Error running Pylint: Not a file: {filename}"
        
        # Run pylint on the file
        result = subprocess.run(
            ["pylint", filename],
            capture_output=True, 
            text=True,
            timeout=30
        )
        
        # Parse and return the report
        return parse_pylint(result.stdout)
        
    except subprocess.TimeoutExpired:
        return "Error running Pylint: Timed out (file too large or complex)"
    except FileNotFoundError:
        return "Error running Pylint: Pylint is not installed. Install with: pip install pylint"
    except Exception as e:
        return f"Error running Pylint: {str(e)}"


def run_pytest(filepath=None):
    """
    Runs Pytest to validate Python code for syntax and runtime errors.
    
    ✅ CORRIGÉ: Teste le code généré par l'agent, pas des fichiers test_*.py externes
    
    Args:
        filepath: Path to the Python file to test (can be None to test all sandbox)
        
    Returns:
        Test results as string with pass/fail information
        
    Examples:
        run_pytest()                        # Tests all .py in sandbox
        run_pytest("sandbox/my_code.py")    # Tests specific file
    """
    try:
        from src.utils.code_validator import SANDBOX_DIR
        
        # ===================================================================
        # DETERMINE WHAT TO TEST
        # ===================================================================
        
        if filepath and os.path.isfile(filepath):
            # Test specific file
            test_target = filepath
            print(f"   🔍 Testing file: {filepath}")
        else:
            # Test entire sandbox
            test_target = SANDBOX_DIR
            print(f"   🔍 Testing directory: {SANDBOX_DIR}")
        
        # ===================================================================
        # RUN PYTEST WITH DOCTEST
        # ===================================================================
        # pytest --doctest-modules teste:
        # 1. Les doctests dans le code (exemples dans les docstrings)
        # 2. Les assertions Python basiques
        # 3. La validité syntaxique
        
        result = subprocess.run(
            [
                "pytest", 
                test_target, 
                "--doctest-modules",  # Active les doctests
                "-v",                 # Verbose
                "--tb=short",         # Traceback concis
                "--color=no"          # Pas de couleurs ANSI
            ],
            capture_output=True, 
            text=True, 
            timeout=30,
            cwd=SANDBOX_DIR  # Run from sandbox for proper imports
        )
        
        # Combine stdout and stderr
        full_output = result.stdout + "\n" + result.stderr
        
        # ===================================================================
        # PARSE RESULTS
        # ===================================================================
        
        if result.returncode == 0:
            # All tests passed
            return "✅ SUCCESS: All tests passed.\n\n" + full_output
        elif result.returncode == 5:
            # No tests found - treat as success for validation
            return "⚠️ NO TESTS: No tests found, but code is syntactically valid.\n\n" + full_output
        else:
            # Tests failed or errors occurred
            return parse_pytest(full_output)
            
    except subprocess.TimeoutExpired:
        return "ERROR: Tests timed out after 30 seconds (possible infinite loop)"
    except FileNotFoundError:
        return "Error running Pytest: Pytest is not installed. Install with: pip install pytest"
    except Exception as e:
        return f"Error running Pytest: {str(e)}"


def write_file(filename, content):
    """
    Writes content to a file in the sandbox.
    
    ⚠️ SECURITY: Only writes to sandbox directory
    
    Args:
        filename: Name of file to write (relative to sandbox)
        content: Content to write to the file
        
    Returns:
        Success message or error message
    """
    try:
        # Validate content is safe
        is_safe, msg = is_safe_code(content)
        if not is_safe:
            return f"Error: Unsafe code detected - {msg}"
        
        # Validate syntax
        is_valid, msg = validate_syntax(content)
        if not is_valid:
            return f"Error: Invalid Python syntax - {msg}"
        
        # Get safe path in sandbox
        path = get_safe_path(filename)
        
        # Write the file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"Successfully wrote {len(content)} characters to {filename}"
        
    except Exception as e:
        return f"Error writing file: {str(e)}"


def list_files():
    """
    Lists all files in the sandbox directory.
    
    Returns:
        List of filenames in sandbox
    """
    try:
        files = []
        for f in os.listdir(SANDBOX_DIR):
            if os.path.isfile(os.path.join(SANDBOX_DIR, f)):
                files.append(f)
        return files
    except Exception as e:
        return f"Error listing files: {str(e)}"