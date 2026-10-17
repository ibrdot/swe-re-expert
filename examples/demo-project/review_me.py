"""Tiny offline fixture for demonstrating audit heuristics. Not production code."""
def route_order(items, express=False):
    total = 0
    for item in items:
        if item > 0:
            if express and item > 100:
                total += item + 10
            else:
                total += item
    if total > 500:
        return total * 0.95
    return total


def unused_candidate():
    return "A low-reference-count candidate, not proof of dead code"


def called_helper():
    return 1


called_helper()
called_helper()
called_helper()
