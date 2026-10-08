import re
from text_utils import slugify


def validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def validate_range(value: float, low: float, high: float) -> bool:
    if low > high:
        raise ValueError("low cannot exceed high")
    if not (low <= value <= high):
        raise ValueError(f"Value {value} is out of range [{low}, {high}]")
    return True


def validate_slug(text: str) -> bool:
    return slugify(text) == text and len(text) > 0

