import os
import ast

BASE_SANDBOX_PATH = os.path.abspath("./sandbox")

def get_safe_path(filename):
    
    # Join the sandbox path with the filename and get the absolute path
    target_path = os.path.abspath(os.path.join(BASE_SANDBOX_PATH, filename))
    
    # Check if the target path starts with the sandbox directory
    if not target_path.startswith(BASE_SANDBOX_PATH):
        raise PermissionError(f"Access Denied: {filename} is outside the sandbox!")
    
    return target_path


def validate_syntax(code_string):
    """Checks if the code is actually valid Python before saving it."""
    try:
        ast.parse(code_string)
        return True, "Success"
    except SyntaxError as e:
        return False, f"Syntax Error at line {e.lineno}: {e.msg}"



def is_safe_code(code_string):
    """Simple check for dangerous commands."""
    forbidden = ["os.remove", "os.rmdir", "shutil.rmtree", "subprocess.run", "import os", "import subprocess"]
    for word in forbidden:
        if word in code_string:
            return False, f"Security Violation: '{word}' is not allowed in the sandbox."
    return True, "Safe"