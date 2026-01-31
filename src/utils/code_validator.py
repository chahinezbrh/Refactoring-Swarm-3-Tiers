import os
import ast

# --------------------------
# Paths
# --------------------------
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_FILE_DIR))
BASE_SANDBOX_PATH = os.path.join(PROJECT_ROOT, "sandbox")
SANDBOX_DIR = BASE_SANDBOX_PATH

os.makedirs(SANDBOX_DIR, exist_ok=True)

# --------------------------
# Helper functions
# --------------------------
def get_safe_path(filename):
    normalized_filename = os.path.normpath(filename)
    target_path = os.path.abspath(os.path.join(BASE_SANDBOX_PATH, normalized_filename))

    if not target_path.startswith(BASE_SANDBOX_PATH + os.sep):
        raise PermissionError(f"Access Denied: '{filename}' is outside the sandbox!")
    return target_path


def validate_syntax(code_string):
    """Checks if the code is valid Python before saving it."""
    try:
        ast.parse(code_string)
        return True, "Valid Python syntax."
    except SyntaxError as e:
        return False, f"Syntax Error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Validation Error: {str(e)}"


def is_safe_code(code_string):
    """Checks for forbidden commands or dangerous operations."""
    forbidden_keywords = [
        "os.remove", "os.rmdir", "shutil.rmtree", "subprocess.run",
        "import os", "import subprocess"
    ]
    for kw in forbidden_keywords:
        if kw in code_string:
            return False, f"Security Violation: '{kw}' is not allowed"

    # AST-based enhanced security check
    try:
        tree = ast.parse(code_string)
    except SyntaxError:
        return True, "Cannot parse for security check (syntax validation will catch it)"

    dangerous_imports = {'os', 'subprocess', 'shutil', 'sys', 'importlib'}
    dangerous_functions = {'eval', 'exec', 'compile', '__import__', 'open', 'input', 'breakpoint'}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in dangerous_imports:
                    return False, f"Forbidden import: '{alias.name}'"
        if isinstance(node, ast.ImportFrom):
            if node.module in dangerous_imports:
                return False, f"Forbidden import: 'from {node.module}'"
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in dangerous_functions:
                return False, f"Forbidden function call: '{node.func.id}()'"
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in ['remove', 'rmdir', 'system', 'popen', 'run', 'call']:
                    return False, f"Forbidden operation: '.{node.func.attr}()'"

    return True, "Code passes security checks."


# --------------------------
# File operations
# --------------------------
def read_file(filename):
    """Reads a file from sandbox and returns its content as string."""
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
    """Writes content to a new _fixed file in sandbox."""
    try:
        name, ext = os.path.splitext(filename)
        new_filename = f"{name}_fixed{ext}"
        path = get_safe_path(new_filename)

        # Security check
        safe, msg = is_safe_code(content)
        if not safe:
            return f"SECURITY ERROR: {msg}"

        # Syntax check
        valid, msg = validate_syntax(content)
        if not valid:
            return f"SYNTAX ERROR: {msg}"

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"SUCCESS: Fixed code saved as '{new_filename}'"
    except Exception as e:
        return f"ERROR: Failed to write file - {str(e)}"

















