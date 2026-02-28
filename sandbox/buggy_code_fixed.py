import math
import random

GLOBAL_LIST = []


def process_data(data, cache=None):
    if cache is None:
        cache = {}
    result = []
    for val in data:
        if val not in cache:
            cache[val] = compute_value(val)
        result.append(cache[val])
    return result


def compute_value(x):
    if x % 2 == 0:
        return x * x
    else:
        return x * 2 + 1


class DataManager:
    def __init__(self, name, items=None):
        self.name = name
        self.items = items if items is not None else []
        self.count = len(self.items)

    def add_item(self, item):
        self.items.append(item)
        self.count += 1

    def remove_item(self, item):
        if item in self.items:
            self.items.remove(item)
            self.count -= 1
        else:
            raise ValueError("Item not found")

    def calculate_average(self):
        if not self.items:
            return 0
        return sum(self.items) / len(self.items)


def inefficient_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr


def read_file(filename):
    try:
        with open(filename, 'r') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return ""


def global_modifier(x):
    GLOBAL_LIST.append(x)
    return GLOBAL_LIST


def main():
    numbers = [1, 2, 3, 4, 5]
    manager1 = DataManager("Test")
    manager2 = DataManager("Another")

    manager1.add_item(10)
    manager2.add_item(20)

    print("Manager1 items:", manager1.items)
    print("Manager2 items:", manager2.items)

    processed = process_data(numbers)
    print("Processed:", processed)

    sorted_numbers = inefficient_sort(numbers)
    print("Sorted:", sorted_numbers)

    content = read_file("non_existent.txt")
    print(content)

    print(global_modifier(100))
    print(global_modifier(200))


if __name__ == "__main__":
    main()