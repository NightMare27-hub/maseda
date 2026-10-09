import pathlib
import re

from rank_bm25 import BM25Okapi

from app.rag.embed import Embedder
from app.rag.ingest import get_collection, index_repo


def _tokens(text: str) -> list[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    out = []
    for token in re.findall(r"[a-z0-9_]+", expanded.lower()):
        out.extend(part for part in token.split("_") if part)
    for token in re.findall(r"[a-z0-9_]+", text.lower()):
        out.append(token)
    return list(dict.fromkeys(out))


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
    where: dict | None = None,
) -> list[dict]:
    collection = get_collection(persist_dir, embedder)
    count = collection.count()
    if count == 0:
        return []
    actual_k = min(k, count)
    query_kwargs = {
        "query_texts": [query],
        "n_results": actual_k,
        "include": ["metadatas", "documents", "distances"],
    }
    if where:
        query_kwargs["where"] = where
    res = collection.query(**query_kwargs)
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
    where: dict | None = None,
) -> list[dict]:
    chunks = _all_chunks(repo_path, persist_dir, embedder)
    if where:
        chunks = [c for c in chunks if all(c.get(k) == v for k, v in where.items())]
    if not chunks:
        return []
    corpus = [_tokens(c["code"] + " " + c["id"] + " " + c["symbol"]) for c in chunks]
    q_tokens = _tokens(query)
    if not q_tokens:
        return [dict(c, score=0.0) for c in chunks[:k]]
    scores = BM25Okapi(corpus).get_scores(q_tokens)
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
    where: dict | None = None,
) -> list[dict]:
    lists = [
        dense(query, k, repo_path, persist_dir, embedder, where=where),
        bm25(query, k, repo_path, persist_dir, embedder, where=where),
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
