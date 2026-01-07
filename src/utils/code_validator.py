import os
import ast

# ✅ Find the project root (go up from src/utils/ to root)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # src/utils/
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))  # Go up 2 levels to root
BASE_SANDBOX_PATH = os.path.join(PROJECT_ROOT, "sandbox")  # root/sandbox
SANDBOX_DIR = BASE_SANDBOX_PATH  # Export for use in other modules


def get_safe_path(filename):
    """
    Ensures the requested file is inside the sandbox directory.
    Prevents path traversal attacks.
    """
    # Normalize the filename to prevent tricks like "../../../etc/passwd"
    normalized_filename = os.path.normpath(filename)
    
    # Join with sandbox and get absolute path
    target_path = os.path.abspath(os.path.join(BASE_SANDBOX_PATH, normalized_filename))
    
    # Verify the target is actually inside the sandbox
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
    """
    Enhanced security check using AST to detect dangerous operations.
    Checks for dangerous imports and function calls.
    """
    try:
        tree = ast.parse(code_string)
    except SyntaxError:
        # If it can't parse, validation will catch it
        return True, "Cannot parse for security check (will fail syntax validation)."
    
    dangerous_imports = {
        'os', 'subprocess', 'shutil', 'sys', 'importlib',
        'eval', 'exec', '__import__', 'compile', 'open'
    }
    
    dangerous_functions = {
        'eval', 'exec', 'compile', '__import__', 'open',
        'input', 'breakpoint'
    }
    
    for node in ast.walk(tree):
        # Check for dangerous imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in dangerous_imports:
                    return False, f"Forbidden import: '{alias.name}'"
        
        # Check for dangerous from imports
        if isinstance(node, ast.ImportFrom):
            if node.module in dangerous_imports:
                return False, f"Forbidden import: 'from {node.module}'"
        
        # Check for dangerous function calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in dangerous_functions:
                    return False, f"Forbidden function call: '{node.func.id}()'"
            # Check for calls like os.remove, subprocess.run, etc.
            elif isinstance(node, ast.Attribute):
                if node.func.attr in ['remove', 'rmdir', 'system', 'popen', 'run', 'call']:
                    return False, f"Forbidden operation: '.{node.func.attr}()'"
    
    return True, "Code passes security checks."