import hashlib
import math
import re
from typing import Protocol


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class ChromaEmbeddingAdapter:
    def __init__(self, embedder: Embedder):
        self.embedder = embedder

    def __call__(self, input: list[str]) -> list[list[float]]:
        return self.embedder.embed(input)

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self.embedder.embed(input)

    def embed_documents(self, input: list[str]) -> list[list[float]]:
        return self.embedder.embed(input)

    def name(self) -> str:
        return "default"


class FakeEmbedder:
    def __init__(self, dimensions: int = 64):
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(text) for text in texts]

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        for token in _tokens(text):
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            vec[h % self.dimensions] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def _tokens(text: str) -> list[str]:
    parts = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+", text)
    out = []
    for part in parts:
        out.extend(x for x in part.lower().split("_") if x)
    return out
