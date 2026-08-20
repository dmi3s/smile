from smile.utils.lerp import lerp


def test_lerp_endpoints():
    assert lerp(0, 100, 0.0) == 0
    assert lerp(0, 100, 1.0) == 100


def test_lerp_midpoint():
    assert lerp(0, 100, 0.5) == 50
    assert lerp(1, 5, 0.8) == 4.2  # from the docstring


def test_lerp_reversed_range():
    assert lerp(100, 0, 0.5) == 50


def test_lerp_out_of_range():
    assert lerp(0, 10, 1.5) == 15
    assert lerp(0, 10, -0.5) == -5
