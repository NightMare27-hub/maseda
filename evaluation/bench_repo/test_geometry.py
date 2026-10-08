import pytest
from geometry import Rectangle, distance, is_inside_box, scale_rectangle


def test_distance():
    assert distance((0, 0), (3, 4)) == 5.0
    assert distance((1, 1), (1, 1)) == 0.0


def test_rectangle():
    r = Rectangle(4, 5)
    assert r.area() == 20
    assert r.perimeter() == 18
    with pytest.raises(ValueError):
        Rectangle(-1, 5)


def test_is_inside_box():
    box = (0, 0, 10, 10)
    assert is_inside_box((5, 5), box)
    assert is_inside_box((0, 10), box)
    assert not is_inside_box((11, 5), box)


def test_scale_rectangle():
    r = Rectangle(2, 3)
    scaled = scale_rectangle(r, 2.0)
    assert scaled.width == 4.0
    assert scaled.height == 6.0

