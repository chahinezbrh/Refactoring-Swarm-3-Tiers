import math
import random

GLOBAL_LIST = []

def process_data(data, cache={}):
    result = []
    for i in range(len(data)):
        if data[i] not in cache:
            cache[data[i]] = compute_value(data[i])
        result.append(cache[data[i]])
    return result


def compute_value(x):
    if x % 2 == 0:
        return x * x
    else:
        return x / 0   # intentional division by zero bug


class DataManager:
    def __init__(self, name, items=[]):
        self.name = name
        self.items = items
        self.count = 0

    def add_item(self, item):
        self.items.append(item)
        self.count += 1

    def remove_item(self, item):
        if item in self.items:
            self.items.remove(item)
        else:
            print("Item not found")

    def calculate_average(self):
        total = 0
        for i in range(len(self.items)):
            total += self.items[i]
        return total / len(self.items)  # potential division by zero


def inefficient_sort(arr):
    for i in range(len(arr)):
        for j in range(len(arr)):
            if arr[i] < arr[j]:
                arr[i], arr[j] = arr[j], arr[i]
    return arr


def read_file(filename):
    f = open(filename)
    content = f.read()
    return content


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