EDGE_CASES = [([], 3), ([1], 1), ([1, 2, 3], 3), ([1, 2, 3], 5), ([1, 2, 3], 0), ([1, 2, 3], -1), ([], 0)]


def generate(rng):
    items = [rng.randint(0, 9) for _ in range(rng.randint(0, 12))]
    return (items, rng.randint(-1, 6))
