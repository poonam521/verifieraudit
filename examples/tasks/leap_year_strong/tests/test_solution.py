import calendar

from solution import is_leap_year


def test_known_years():
    assert is_leap_year(2000) is True
    assert is_leap_year(1900) is False
    assert is_leap_year(2024) is True
    assert is_leap_year(2023) is False


def test_every_year_matches_the_calendar_module():
    for year in range(1, 4001):
        assert is_leap_year(year) is calendar.isleap(year), year
