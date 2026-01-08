# corrected_code.py - Test file with corrections

def calculate_average(numbers):
    """Calculates the average of a list of numbers, handling empty lists gracefully."""
    # FIX 1: Prevent ZeroDivisionError if the list is empty.
    if not numbers:
        return None
    
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

def find_maximum(lst):
    """Finds the maximum value in a list, handling empty lists."""
    # FIX 2: Prevent IndexError if the list is empty.
    if not lst:
        return None
        
    # Note: Using Python's built-in max(lst) is generally preferred, 
    # but maintaining the original loop structure for correction purposes.
    max_val = lst[0]
    for item in lst:
        if item > max_val:
            max_val = item
    return max_val

def greet_user(name):
    # The original code was syntactically correct here.
    print(f"Hello, {name}")

class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, x, y):
        self.result = x + y
        return self.result
    
    def divide(self, x, y):
        """Performs division, raising a ValueError if the divisor is zero."""
        # FIX 3: Check for division by zero.
        if y == 0:
            raise ValueError("Cannot divide by zero.")
        return x / y

# Main execution
if __name__ == "__main__":
    print("--- Testing calculate_average ---")
    numbers = [1, 2, 3, 4, 5]
    avg = calculate_average(numbers)
    print(f"Average of {numbers}: {avg}")
    
    empty_numbers = []
    avg_empty = calculate_average(empty_numbers)
    print(f"Average of empty list: {avg_empty}")
    
    print("\n--- Testing find_maximum ---")
    empty_list = []
    # The function is now robust and returns None for empty lists.
    max_num = find_maximum(empty_list)
    
    if max_num is None:
        print("Maximum of empty list: Undefined (handled gracefully)")
    else:
        print(f"Maximum number: {max_num}")
        
    print("\n--- Testing greet_user ---")
    greet_user("Alice")

    print("\n--- Testing Calculator ---")
    calc = Calculator()
    print(f"Addition (10 + 5): {calc.add(10, 5)}")
    
    # Testing the fixed division method
    print(f"Division (10 / 2): {calc.divide(10, 2)}")
    
    try:
        print("Attempting division by zero...")
        calc.divide(10, 0)
    except ValueError as e:
        print(f"Division Error Handled: {e}")