EDGE_CASES = [([], 1), ([5], 5), ([5], 4), ([5], 6), ([1, 3, 5, 7], 0), ([1, 3, 5, 7], 8), ([1, 3, 5, 7], 4)]


def generate(rng):
    items = sorted(rng.sample(range(0, 60), rng.randint(0, 15)))
    if items and rng.random() < 0.5:
        return (items, rng.choice(items))
    return (items, rng.randint(-2, 62))
