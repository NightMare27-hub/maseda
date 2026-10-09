import pathlib

import chromadb

from app.rag.chunk import chunk_python_file
from app.rag.embed import ChromaEmbeddingAdapter, Embedder

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "chroma_db"}
COLLECTION = "maseda_code"


def iter_py_files(repo_path: str | pathlib.Path) -> list[pathlib.Path]:
    root = pathlib.Path(repo_path)
    out = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if set(rel.parts) & SKIP_DIRS or ".env" in rel.parts:
            continue
        out.append(path)
    return out


def get_collection(persist_dir: str | pathlib.Path = "chroma_db", embedder: Embedder | None = None):
    client = chromadb.PersistentClient(path=str(persist_dir))
    ef = ChromaEmbeddingAdapter(embedder) if embedder else None
    return client.get_or_create_collection(COLLECTION, embedding_function=ef)


def index_repo(
    repo_path: str | pathlib.Path,
    persist_dir: str | pathlib.Path = "chroma_db",
    embedder: Embedder | None = None,
):
    root = pathlib.Path(repo_path)
    chunks = []
    for path in iter_py_files(root):
        chunks.extend(chunk_python_file(path, root))
    collection = get_collection(persist_dir, embedder)
    if not chunks:
        return collection, []
    collection.upsert(
        ids=[c["id"] for c in chunks],
        documents=[c["code"] for c in chunks],
        metadatas=[c.copy() for c in chunks],
    )
    return collection, chunks
