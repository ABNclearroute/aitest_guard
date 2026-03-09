"""Calculator module with public functions for aitest-guard enforcement demo."""


def calculate_total(items: list[float]) -> float:
    """Sum numeric items. Empty list returns 0."""
    if not items:
        return 0.0
    total = 0.0
    for x in items:
        total += float(x)
    return total
