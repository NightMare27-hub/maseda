import argparse
import sys
from pathlib import Path

from app.rag.retrieve import bm25, dense, hybrid


def search_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Search repository code using AST-indexed RAG (Dense, BM25, or Hybrid)."
    )
    parser.add_argument("query", help="Natural language query or code symbol to search for.")
    parser.add_argument(
        "--mode",
        choices=["dense", "bm25", "hybrid"],
        default="hybrid",
        help="Retrieval mode (default: hybrid).",
    )
    parser.add_argument("-k", type=int, default=5, help="Number of results to return (default: 5).")
    parser.add_argument("--repo", default=".", help="Target repository path (default: current directory).")
    parser.add_argument(
        "--persist-dir",
        default="chroma_db",
        help="ChromaDB persistence directory (default: chroma_db).",
    )
    parser.add_argument("--kind", choices=["function", "class", "method", "module"], help="Filter by symbol kind.")
    parser.add_argument("--file", help="Filter by relative file path.")
    parser.add_argument("--mock", action="store_true", help="Use offline FakeEmbedder for testing.")

    args = parser.parse_args(argv)

    where = {}
    if args.kind:
        where["kind"] = args.kind
    if args.file:
        where["file"] = args.file
    where_filter = where if where else None

    embedder = None
    if args.mock:
        from app.rag.embed import FakeEmbedder

        embedder = FakeEmbedder()

    fn_map = {"dense": dense, "bm25": bm25, "hybrid": hybrid}
    search_fn = fn_map[args.mode]

    print(f"\n[*] Searching for: '{args.query}' [Mode: {args.mode.upper()}, k={args.k}]")
    if where_filter:
        print(f"   Filter: {where_filter}")
    print("=" * 70)

    results = search_fn(
        query=args.query,
        k=args.k,
        repo_path=args.repo,
        persist_dir=args.persist_dir,
        embedder=embedder,
        where=where_filter,
    )

    if not results:
        print("[-] No matching code chunks found.")
        print("=" * 70)
        return 0

    for idx, r in enumerate(results, start=1):
        score_display = f"{r.get('score', 0.0):.4f}"
        file_line = f"{r.get('file', 'unknown')}:{r.get('start_line', '?')}-{r.get('end_line', '?')}"
        tokens = r.get("token_estimate", "?")
        print(f"#{idx} | {r.get('symbol', 'unknown')} ({r.get('kind', 'unknown')})")
        print(f"    Location: {file_line} | Score: {score_display} | Est. Tokens: {tokens}")
        print("    " + "-" * 62)
        code_lines = r.get("code", "").splitlines()
        preview = code_lines[:12]
        for line in preview:
            print(f"    {line}")
        if len(code_lines) > 12:
            print(f"    ... [{len(code_lines) - 12} more lines]")
        print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(search_cli())
