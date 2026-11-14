_PAIRS = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
          (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def _to_roman(number):
    out = []
    for value, symbols in _PAIRS:
        while number >= value:
            out.append(symbols)
            number -= value
    return "".join(out)


EDGE_CASES = [("I",), ("IV",), ("IX",), ("XL",), ("XC",), ("CD",), ("CM",), ("MCMXCIV",), ("MMMCMXCIX",)]


def generate(rng):
    return (_to_roman(rng.randint(1, 3999)),)
