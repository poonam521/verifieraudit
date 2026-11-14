import random

from solution import binary_search


def test_middle():
    assert binary_search([1, 3, 5, 7, 9], 5) == 2


def test_first_and_last():
    assert binary_search([1, 3, 5, 7, 9], 1) == 0
    assert binary_search([1, 3, 5, 7, 9], 9) == 4


def test_single_item():
    assert binary_search([7], 7) == 0


def test_random_lists():
    rng = random.Random(1234)
    for _ in range(300):
        items = sorted(rng.sample(range(100), rng.randint(1, 20)))
        target = rng.choice(items)
        assert items[binary_search(items, target)] == target
