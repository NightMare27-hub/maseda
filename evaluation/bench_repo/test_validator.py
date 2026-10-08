import pytest
from validator import validate_email, validate_range, validate_slug


def test_validate_email():
    assert validate_email("user@example.com")
    assert not validate_email("invalid-email")
    assert not validate_email("@no-user.com")


def test_validate_range():
    assert validate_range(5, 0, 10) is True
    with pytest.raises(ValueError):
        validate_range(15, 0, 10)
    with pytest.raises(ValueError):
        validate_range(5, 10, 0)


def test_validate_slug():
    assert validate_slug("valid-slug-123") is True
    assert validate_slug("Invalid Slug") is False
    assert validate_slug("") is False

