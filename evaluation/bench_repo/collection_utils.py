def chunk_list(lst: list, size: int) -> list:
    if size <= 0:
        raise ValueError("Chunk size must be positive")
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def flatten(nested_list: list) -> list:
    out = []
    for item in nested_list:
        if isinstance(item, list):
            out.extend(flatten(item))
        else:
            out.append(item)
    return out


def deduplicate(items: list) -> list:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def find_first(predicate, iterable, default=None):
    for item in iterable:
        if predicate(item):
            return item
    return default

