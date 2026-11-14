import pytest

import solution
from solution import chunk


def test_even_split():
    assert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_uneven_split():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_size_one():
    assert chunk([7, 8, 9], 1) == [[7], [8], [9]]


def test_size_equal_to_length():
    assert chunk([1, 2, 3], 3) == [[1, 2, 3]]


def test_size_larger_than_list():
    assert chunk([1, 2], 5) == [[1, 2]]


def test_empty_list():
    assert chunk([], 3) == []


def test_every_split_of_a_longer_list():
    items = list(range(11))
    for size in range(1, 13):
        parts = chunk(items, size)
        assert [x for part in parts for x in part] == items
        assert all(len(part) == size for part in parts[:-1])
        assert 1 <= len(parts[-1]) <= size


@pytest.mark.parametrize("size", [0, -1, -5])
def test_bad_size(size):
    with pytest.raises(ValueError, match="size must be a positive integer"):
        chunk([1, 2, 3], size)
    with pytest.raises(ValueError):
        chunk([], size)


def test_validation_helper():
    solution._validate_size(1)
    with pytest.raises(ValueError):
        solution._validate_size(0)
