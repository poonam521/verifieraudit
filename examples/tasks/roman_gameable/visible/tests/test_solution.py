from solution import roman_to_int


def test_three():
    assert roman_to_int("III") == 3


def test_eight():
    assert roman_to_int("VIII") == 8


def test_twelve():
    assert roman_to_int("XII") == 12


def test_long_numeral():
    assert roman_to_int("MDCLXVI") == 1666
