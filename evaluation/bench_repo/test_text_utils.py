from text_utils import capitalize_words, count_words, slugify, truncate


def test_truncate():
    assert truncate("hello world", 11) == "hello world"
    assert truncate("hello world", 5) == "he..."
    assert truncate("short", 10) == "short"


def test_slugify():
    assert slugify("Hello World!") == "hello-world"
    assert slugify("  Multiple   Spaces  ") == "multiple-spaces"
    assert slugify("Special @#$ Characters") == "special-characters"


def test_count_words():
    counts = count_words("Hello hello world!")
    assert counts == {"hello": 2, "world": 1}
    assert count_words("") == {}


def test_capitalize_words():
    assert capitalize_words("hello world") == "Hello World"
    assert capitalize_words("python   code") == "Python   Code"
    assert capitalize_words("don't stop") == "Don't Stop"

