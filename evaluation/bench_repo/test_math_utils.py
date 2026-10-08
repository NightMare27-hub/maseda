import pytest
from math_utils import add, clamp, factorial, fibonacci, is_prime, power


def test_add():
    assert add(2, 3) == 5


def test_factorial():
    assert factorial(0) == 1
    assert factorial(1) == 1
    assert factorial(5) == 120
    with pytest.raises(ValueError):
        factorial(-1)


def test_is_prime():
    assert not is_prime(0)
    assert not is_prime(1)
    assert is_prime(2)
    assert is_prime(13)
    assert not is_prime(15)


def test_fibonacci():
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1
    assert fibonacci(7) == 13
    with pytest.raises(ValueError):
        fibonacci(-2)


def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-5, 0, 10) == 0
    assert clamp(15, 0, 10) == 10
    with pytest.raises(ValueError):
        clamp(5, 10, 0)


def test_power():
    assert power(2, 3) == 8
    assert power(5, 0) == 1

