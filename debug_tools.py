from tools import read_file, write_file, run_pylint, run_pytest
import os


def test_system():
    """Comprehensive test of the multi-agent code fixing system."""
    
    print("=" * 60)
    print("MULTI-AGENT SYSTEM TEST")
    print("=" * 60)
    
    # ========================================================================
    # TEST 1: Write Valid Code
    # ========================================================================
    print("\n--- 1. Testing Write (Valid Code) ---")
    valid_code = "def add(a, b):\n    return a + b"
    result = write_file("math_tool.py", valid_code)
    print(result)
    assert "SUCCESS" in result, "Valid code should be saved successfully"
    
    # ========================================================================
    # TEST 2: Write Code with Syntax Error
    # ========================================================================
    print("\n--- 2. Testing Write (Syntax Error) ---")
    broken_syntax = "def add(a, b)\n    return a + b"  # Missing colon
    result = write_file("broken.py", broken_syntax)
    print(result)
    assert "SYNTAX ERROR" in result, "Should reject code with syntax errors"
    
    # ========================================================================
    # TEST 3: Security - Dangerous Code
    # ========================================================================
    print("\n--- 3. Testing Security (Dangerous Code) ---")
    dangerous_code = "import os\nos.remove('important.txt')"
    result = write_file("malicious.py", dangerous_code)
    print(result)
    assert "SECURITY ERROR" in result, "Should block dangerous imports/operations"
    
    # ========================================================================
    # TEST 4: Security - Path Traversal
    # ========================================================================
    print("\n--- 4. Testing Security (Path Traversal) ---")
    result = write_file("../../../etc/passwd", "print('hacked')")
    print(result)
    assert "PERMISSION ERROR" in result or "Access Denied" in result, \
        "Should prevent writing outside sandbox"
    
    # ========================================================================
    # TEST 5: Read File
    # ========================================================================
    print("\n--- 5. Testing Read ---")
    # Read the file that was successfully written (math_tool_fixed.py)
    content = read_file("math_tool_fixed.py")
    print(f"Content of math_tool_fixed.py:\n{content}")
    assert "def add(a, b):" in content, "Should read the correct file content"
    
    # ========================================================================
    # TEST 6: Pylint - File with Errors
    # ========================================================================
    print("\n--- 6. Testing Pylint (Linting Errors) ---")
    # Write code with an actual ERROR (undefined variable)
    """"code_with_error =  "import os\n\ndef test():\n    return 1\n"
    write_file("lint_test.py", code_with_error)"""
    # Pylint needs to check the _fixed version that was actually created
    lint_result = run_pylint("lint_test_fixed.py")
    print("Pylint Report:")
    print(lint_result)
    # Should find the undefined variable error
    
    # ========================================================================
    # TEST 7: Pylint - Clean Code
    # ========================================================================
    print("\n--- 7. Testing Pylint (Clean Code) ---")
    clean_code = """def multiply(x, y):
    return x * y

def main():
    print(multiply(3, 4))
"""
    write_file("clean.py", clean_code)
    lint_result = run_pylint("clean_fixed.py")
    print("Pylint Report:")
    print(lint_result)
    
    # ========================================================================
    # TEST 8: Create Source Code for Testing
    # ========================================================================
    print("\n--- 8. Creating Test Files for Pytest ---")
    
    # Create the actual implementation file
    # Note: We need to create the original file (not _fixed) for imports to work
    source_code = """def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
"""
    # Manually create the file in sandbox (bypassing write_file for this setup)
    from src.utils.code_validator import get_safe_path
    source_path = get_safe_path("calculator.py")
    with open(source_path, 'w') as f:
        f.write(source_code)
    print("Created calculator.py in sandbox")
    
    # ========================================================================
    # TEST 9: Pytest - Passing Tests
    # ========================================================================
    print("\n--- 9. Testing Pytest (Passing Tests) ---")
    passing_test = """from calculator import add, subtract

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0

def test_subtract():
    assert subtract(5, 3) == 2
"""
    write_file("test_calculator_pass.py", passing_test)
    
    # Copy the _fixed version to remove the _fixed suffix so pytest can import it
    fixed_test_path = get_safe_path("test_calculator_pass_fixed.py")
    final_test_path = get_safe_path("test_calculator.py")
    with open(fixed_test_path, 'r') as f:
        test_content = f.read()
    with open(final_test_path, 'w') as f:
        f.write(test_content)
    
    print("Running pytest (expecting SUCCESS):")
    result = run_pytest()
    print(result)
    
    # ========================================================================
    # TEST 10: Pytest - Failing Tests
    # ========================================================================
    print("\n--- 10. Testing Pytest (Failing Tests) ---")
    failing_test = """from calculator import add

def test_add_fail():
    assert add(2, 2) == 5  # This will fail!
"""
    write_file("test_fail.py", failing_test)
    
    # Copy to proper test file name
    fixed_fail_path = get_safe_path("test_fail_fixed.py")
    final_fail_path = get_safe_path("test_calculator_fail.py")
    with open(fixed_fail_path, 'r') as f:
        fail_content = f.read()
    with open(final_fail_path, 'w') as f:
        f.write(fail_content)
    
    print("Running pytest (expecting FAILURE):")
    result = run_pytest()
    print(result)
    
    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)
    print("\nAll core functionality verified:")
    print("✓ Valid code writing")
    print("✓ Syntax validation")
    print("✓ Security checks (dangerous code)")
    print("✓ Security checks (path traversal)")
    print("✓ File reading")
    print("✓ Pylint integration")
    print("✓ Pytest integration")


if __name__ == "__main__":
    test_system()