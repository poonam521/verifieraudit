EDGE_CASES = [(0,), (1,), (5,), (20,), (21,), (0.5,), (-1,)]


def generate(rng):
    if rng.random() < 0.5:
        return (rng.randint(-2, 40),)
    return (round(rng.uniform(-1, 40), 1),)
