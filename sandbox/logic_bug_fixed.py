def count_down(n: int) -> None:
    """Prints numbers from n down to 1."""
    if not isinstance(n, int):
        return
    while n > 0:
        print(n)
        n -= 1