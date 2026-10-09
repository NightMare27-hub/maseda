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


def test_chunk_syntax_error_fallback(tmp_path):
    broken = tmp_path / "broken.py"
    broken.write_text("def broken(:\n    pass\n", encoding="utf-8")
    chunks = chunk_python_file(broken, tmp_path)
    assert len(chunks) == 1
    assert chunks[0]["symbol"] == "module"
    assert chunks[0]["kind"] == "module"
    assert "def broken(:" in chunks[0]["code"]


def _rank(results, expected):
    for idx, r in enumerate(results, start=1):
        if r.get("symbol") == expected:
            return idx
    return 0


def _reciprocal_rank(results, expected):
    rank = _rank(results, expected)
    return 1.0 / rank if rank > 0 else 0.0


@pytest.mark.slow
def test_recall_at_5_real_embedder(tmp_path, monkeypatch):
    from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

    monkeypatch.setattr(ONNXMiniLM_L6_V2, "DOWNLOAD_PATH", tmp_path / "model_cache")
    persist = tmp_path / "chroma"
    index_repo(BENCH, persist)

    d_r1, d_r5, d_rr = 0, 0, 0.0
    b_r1, b_r5, b_rr = 0, 0, 0.0
    h_r1, h_r5, h_rr = 0, 0, 0.0

    for query, expected in RECALL_QUERIES:
        d_res = dense(query, 5, BENCH, persist)
        b_res = bm25(query, 5, BENCH, persist)
        h_res = hybrid(query, 5, BENCH, persist)

        d_r = _rank(d_res, expected)
        b_r = _rank(b_res, expected)
        h_r = _rank(h_res, expected)

        if d_r == 1:
            d_r1 += 1
        if 1 <= d_r <= 5:
            d_r5 += 1
        d_rr += 1.0 / d_r if d_r > 0 else 0.0

        if b_r == 1:
            b_r1 += 1
        if 1 <= b_r <= 5:
            b_r5 += 1
        b_rr += 1.0 / b_r if b_r > 0 else 0.0

        if h_r == 1:
            h_r1 += 1
        if 1 <= h_r <= 5:
            h_r5 += 1
        h_rr += 1.0 / h_r if h_r > 0 else 0.0

    total = len(RECALL_QUERIES)
    print(
        f"\n--- IR Benchmark Evaluation ({total} Queries) ---\n"
        f"Dense:  Recall@1={d_r1/total:.2%}, Recall@5={d_r5/total:.2%}, MRR={d_rr/total:.4f}\n"
        f"BM25:   Recall@1={b_r1/total:.2%}, Recall@5={b_r5/total:.2%}, MRR={b_rr/total:.4f}\n"
        f"Hybrid: Recall@1={h_r1/total:.2%}, Recall@5={h_r5/total:.2%}, MRR={h_rr/total:.4f}\n"
        f"------------------------------------------------"
    )
    assert d_r5 / total >= 0.80
