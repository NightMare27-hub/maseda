import re


def truncate(text: str, max_len: int, suffix: str = "...") -> str:
    if len(text) <= max_len:
        return text
    if max_len < len(suffix):
        return text[:max_len]
    return text[: max_len - len(suffix)] + suffix


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def count_words(text: str) -> dict:
    words = re.findall(r"\b\w+\b", text.lower())
    counts = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    return counts


def capitalize_words(text: str) -> str:
    return " ".join(word.capitalize() for word in text.split(" "))

