import pytest

from solution import shipping_fee


def test_light_parcel():
    assert shipping_fee(0.5) == 4.0


def test_medium_parcel():
    assert shipping_fee(3) == 7.5


def test_heavy_parcel():
    assert shipping_fee(10) == 15.0


def test_very_heavy_parcel():
    assert shipping_fee(30) == 27.0


def test_negative_weight_is_rejected():
    with pytest.raises(ValueError):
        shipping_fee(-1)
