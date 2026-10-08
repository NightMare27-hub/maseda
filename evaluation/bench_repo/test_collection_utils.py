import pytest
from collection_utils import chunk_list, deduplicate, find_first, flatten


def test_chunk_list():
    assert chunk_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert chunk_list([], 3) == []
    with pytest.raises(ValueError):
        chunk_list([1, 2], 0)
    with pytest.raises(ValueError):
        chunk_list([1, 2], -1)


def test_flatten():
    assert flatten([1, [2, [3, 4], 5], 6]) == [1, 2, 3, 4, 5, 6]
    assert flatten([]) == []


def test_deduplicate():
    assert deduplicate([3, 1, 3, 2, 1, 4]) == [3, 1, 2, 4]
    assert deduplicate([]) == []


def test_find_first():
    assert find_first(lambda x: x > 3, [1, 2, 5, 4]) == 5
    assert find_first(lambda x: x < 0, [1, 2, 3], default=-1) == -1

