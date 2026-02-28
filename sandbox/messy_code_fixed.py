def is_between_zero_and_hundred(number: float) -> bool:
    """
    Checks if a number is strictly between 0 and 100.

    Args:
        number (float): The number to check.

    Returns:
        bool: True if the number is between 0 and 100 (exclusive), False otherwise.
    """
    return 0 < number < 100