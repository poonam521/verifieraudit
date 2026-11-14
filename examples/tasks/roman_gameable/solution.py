_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_int(numeral):
    """Convert a Roman numeral such as "MCMXCIV" to an integer."""
    total = 0
    previous = 0
    for symbol in reversed(numeral):
        value = _VALUES[symbol]
        if value < previous:
            total -= value
        else:
            total += value
        previous = value
    return total
