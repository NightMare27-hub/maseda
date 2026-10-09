from pathlib import Path

import pytest

from app.rag.chunk import chunk_python_file
from app.rag.embed import FakeEmbedder
from app.rag.ingest import index_repo
from app.rag.retrieve import bm25, dense, hybrid

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "evaluation" / "bench_repo"


def test_chunk_ids_and_metadata():
    chunks = chunk_python_file(BENCH / "geometry.py", BENCH)
    by_id = {c["id"]: c for c in chunks}

    assert "geometry.py::module" in by_id
    assert "geometry.py::distance" in by_id
    assert "geometry.py::Rectangle" in by_id
    assert "geometry.py::Rectangle.area" in by_id

    method = by_id["geometry.py::Rectangle.area"]
    assert method["file"] == "geometry.py"
    assert method["symbol"] == "Rectangle.area"
    assert method["kind"] == "method"
    assert method["parent_class"] == "Rectangle"
    assert method["start_line"] <= method["end_line"]
    assert "class Rectangle:" in method["code"]
    assert "def area" in method["code"]


def test_dense_retrieval_with_fake_embedder(tmp_path):
    embedder = FakeEmbedder()
    index_repo(BENCH, tmp_path / "chroma", embedder)

    results = dense("clamp value between min_val and max_val", 5, BENCH, tmp_path / "chroma", embedder)

    assert any(r["symbol"] == "clamp" for r in results)
    assert all("score" in r for r in results)


def test_bm25_retrieval(tmp_path):
    embedder = FakeEmbedder()
    index_repo(BENCH, tmp_path / "chroma", embedder)

    results = bm25("validate slug uses slugify", 5, BENCH, tmp_path / "chroma", embedder)

    assert any(r["symbol"] == "validate_slug" for r in results)


def test_hybrid_rrf_ordering_and_dedupe(monkeypatch):
    from app.rag import retrieve

    monkeypatch.setattr(
        retrieve,
        "dense",
        lambda *a, **k: [
            {"id": "a", "symbol": "a", "score": 0.9},
            {"id": "b", "symbol": "b", "score": 0.8},
        ],
    )
    monkeypatch.setattr(
        retrieve,
        "bm25",
        lambda *a, **k: [
            {"id": "b", "symbol": "b", "score": 3.0},
            {"id": "c", "symbol": "c", "score": 2.0},
        ],
    )

    results = hybrid("query", 3)

    assert [r["id"] for r in results] == ["b", "a", "c"]
    assert len({r["id"] for r in results}) == 3


RECALL_QUERIES = [
    ("factorial negative input", "factorial"),
    ("prime number check", "is_prime"),
    ("fibonacci sequence negative", "fibonacci"),
    ("clamp between min and max", "clamp"),
    ("raise base to exponent", "power"),
    ("truncate text suffix max length", "truncate"),
    ("make lowercase url slug", "slugify"),
    ("count word occurrences punctuation", "count_words"),
    ("capitalize every word preserve spaces", "capitalize_words"),
    ("split list into chunks", "chunk_list"),
    ("flatten nested list recursively", "flatten"),
    ("remove duplicate items preserve order", "deduplicate"),
    ("first item matching predicate default", "find_first"),
    ("euclidean distance between points", "distance"),
    ("email validation username domain", "validate_email"),
]


def _recall(results, expected):
    return any(r["symbol"] == expected for r in results)


@pytest.mark.slow
def test_recall_at_5_real_embedder(tmp_path, monkeypatch):
    from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

    monkeypatch.setattr(ONNXMiniLM_L6_V2, "DOWNLOAD_PATH", tmp_path / "model_cache")
    persist = tmp_path / "chroma"
    index_repo(BENCH, persist)

    dense_hits = 0
    bm25_hits = 0
    hybrid_hits = 0
    for query, expected in RECALL_QUERIES:
        dense_hits += _recall(dense(query, 5, BENCH, persist), expected)
        bm25_hits += _recall(bm25(query, 5, BENCH, persist), expected)
        hybrid_hits += _recall(hybrid(query, 5, BENCH, persist), expected)

    total = len(RECALL_QUERIES)
    print(
        f"recall@5 dense={dense_hits / total:.2%} "
        f"bm25={bm25_hits / total:.2%} hybrid={hybrid_hits / total:.2%}"
    )
    assert dense_hits / total >= 0.80
