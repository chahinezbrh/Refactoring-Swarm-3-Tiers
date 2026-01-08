# buggy_code.py - Test file with bugs

def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)  # BUG: Division by zero if empty list

def find_maximum(lst):
    max_val = lst[0]  # BUG: IndexError if list is empty
    for item in lst:
        if item > max_val:
            max_val = item
    return max_val

def greet_user(name):
    print(f"Hello, {name}")  # BUG: Typo - should be 'name'

class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, x, y):
        self.result = x + y
        return self.result
    
    def divide(self, x, y):
        return x / y  # BUG: No check for division by zero

# Main execution
if __name__ == "__main__":
    numbers = [1, 2, 3, 4, 5]
    avg = calculate_average(numbers)
    print(f"Average: {avg}")
    
    empty_list = []
    max_num = find_maximum(empty_list)  # This will crash
    
    greet_user("Alice")