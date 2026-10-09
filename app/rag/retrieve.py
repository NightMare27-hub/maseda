import pathlib
import re

from rank_bm25 import BM25Okapi

from app.rag.embed import Embedder
from app.rag.ingest import get_collection, index_repo


def _tokens(text: str) -> list[str]:
    out = []
    for token in re.findall(r"[a-z0-9_]+", text.lower()):
        out.extend(part for part in token.split("_") if part)
    return out


def _all_chunks(repo_path: str | pathlib.Path, persist_dir: str | pathlib.Path, embedder: Embedder | None):
    collection, _ = index_repo(repo_path, persist_dir, embedder)
    data = collection.get(include=["metadatas", "documents"])
    chunks = []
    for meta, doc in zip(data.get("metadatas", []), data.get("documents", [])):
        c = dict(meta)
        c["code"] = doc
        chunks.append(c)
    return chunks


def dense(
    query: str,
    k: int = 5,
    repo_path: str | pathlib.Path = ".",
    persist_dir: str | pathlib.Path = "chroma_db",
    embedder: Embedder | None = None,
) -> list[dict]:
    collection = get_collection(persist_dir, embedder)
    res = collection.query(query_texts=[query], n_results=k, include=["metadatas", "documents", "distances"])
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    out = []
    for meta, doc, dist in zip(metas, docs, dists):
        c = dict(meta)
        c["code"] = doc
        c["score"] = 1.0 / (1.0 + float(dist))
        out.append(c)
    return out


def bm25(
    query: str,
    k: int = 5,
    repo_path: str | pathlib.Path = ".",
    persist_dir: str | pathlib.Path = "chroma_db",
    embedder: Embedder | None = None,
) -> list[dict]:
    chunks = _all_chunks(repo_path, persist_dir, embedder)
    if not chunks:
        return []
    corpus = [_tokens(c["code"] + " " + c["id"] + " " + c["symbol"]) for c in chunks]
    scores = BM25Okapi(corpus).get_scores(_tokens(query))
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)[:k]
    out = []
    for chunk, score in ranked:
        c = dict(chunk)
        c["score"] = float(score)
        out.append(c)
    return out


def hybrid(
    query: str,
    k: int = 5,
    repo_path: str | pathlib.Path = ".",
    persist_dir: str | pathlib.Path = "chroma_db",
    embedder: Embedder | None = None,
) -> list[dict]:
    lists = [
        dense(query, k, repo_path, persist_dir, embedder),
        bm25(query, k, repo_path, persist_dir, embedder),
    ]
    by_id = {}
    scores = {}
    for results in lists:
        for rank, chunk in enumerate(results, start=1):
            cid = chunk["id"]
            by_id[cid] = chunk
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (60 + rank)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
    out = []
    for cid, score in ranked:
        c = dict(by_id[cid])
        c["score"] = score
        out.append(c)
    return out
