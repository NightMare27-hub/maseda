import argparse
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.rag.embed import FakeEmbedder
from app.rag.ingest import index_repo
from app.rag.retrieve import bm25, dense, hybrid

BENCH = ROOT / "evaluation" / "bench_repo"
RESULTS_DIR = ROOT / "evaluation" / "results"

BENCHMARK_QUERIES = [
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


def _find_rank(results: list[dict], target_symbol: str) -> int:
    for idx, r in enumerate(results, start=1):
        if r.get("symbol") == target_symbol:
            return idx
    return 0


def run_rag_eval(mock: bool = False, persist_dir: Path | None = None) -> dict:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    embedder = FakeEmbedder() if mock else None
    actual_persist = persist_dir or (RESULTS_DIR / "chroma_eval")
    shutil.rmtree(actual_persist, ignore_errors=True)

    print(f"\n[*] Running RAG Retrieval Evaluation Benchmark (Mock={mock})...")
    print(f"    Target Repository: {BENCH}")
    print(f"    Queries Count: {len(BENCHMARK_QUERIES)}\n")

    t0 = time.time()
    index_repo(BENCH, actual_persist, embedder)
    indexing_time = time.time() - t0

    records = []
    stats = {
        "dense": {"r1": 0, "r3": 0, "r5": 0, "mrr_sum": 0.0},
        "bm25": {"r1": 0, "r3": 0, "r5": 0, "mrr_sum": 0.0},
        "hybrid": {"r1": 0, "r3": 0, "r5": 0, "mrr_sum": 0.0},
    }

    for query, expected in BENCHMARK_QUERIES:
        d_res = dense(query, 5, BENCH, actual_persist, embedder)
        b_res = bm25(query, 5, BENCH, actual_persist, embedder)
        h_res = hybrid(query, 5, BENCH, actual_persist, embedder)

        d_rank = _find_rank(d_res, expected)
        b_rank = _find_rank(b_res, expected)
        h_rank = _find_rank(h_res, expected)

        for mode, rank in [("dense", d_rank), ("bm25", b_rank), ("hybrid", h_rank)]:
            if rank == 1:
                stats[mode]["r1"] += 1
            if 1 <= rank <= 3:
                stats[mode]["r3"] += 1
            if 1 <= rank <= 5:
                stats[mode]["r5"] += 1
            if rank > 0:
                stats[mode]["mrr_sum"] += 1.0 / rank

        records.append({
            "query": query,
            "expected": expected,
            "dense_rank": d_rank or "-",
            "bm25_rank": b_rank or "-",
            "hybrid_rank": h_rank or "-",
        })

    total = len(BENCHMARK_QUERIES)
    summary = {}
    for mode in ["dense", "bm25", "hybrid"]:
        summary[mode] = {
            "recall@1": stats[mode]["r1"] / total,
            "recall@3": stats[mode]["r3"] / total,
            "recall@5": stats[mode]["r5"] / total,
            "mrr": stats[mode]["mrr_sum"] / total,
        }

    report_md = _generate_report_markdown(records, summary, indexing_time, mock)
    output_file = RESULTS_DIR / "rag_retrieval_report.md"
    output_file.write_text(report_md, encoding="utf-8")
    print(f"[+] Detailed academic report saved to: {output_file}")

    _print_terminal_summary(summary)
    return summary


def _print_terminal_summary(summary: dict):
    print("=" * 70)
    print("MODE      | RECALL@1 | RECALL@3 | RECALL@5 | MRR")
    print("-" * 70)
    for mode in ["dense", "bm25", "hybrid"]:
        s = summary[mode]
        print(f"{mode.upper():<9} | {s['recall@1']:>8.2%} | {s['recall@3']:>8.2%} | {s['recall@5']:>8.2%} | {s['mrr']:>6.4f}")
    print("=" * 70 + "\n")


def _generate_report_markdown(records: list[dict], summary: dict, index_time: float, mock: bool) -> str:
    md = [
        "# RAG Retrieval Benchmark Report",
        f"\n* **Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"* **Mode**: {'Mock Offline Embedder' if mock else 'Local ONNX all-MiniLM-L6-v2'}",
        f"* **Indexing Time**: {index_time:.2f}s",
        f"* **Queries Evaluated**: {len(records)}",
        "\n## 1. Summary Performance Metrics\n",
        "| Retrieval Mode | Recall@1 | Recall@3 | Recall@5 | MRR (Mean Reciprocal Rank) |",
        "|---|:---:|:---:|:---:|:---:|",
    ]
    for mode in ["dense", "bm25", "hybrid"]:
        s = summary[mode]
        md.append(f"| **{mode.capitalize()}** | {s['recall@1']:.2%} | {s['recall@3']:.2%} | {s['recall@5']:.2%} | {s['mrr']:.4f} |")

    md.extend([
        "\n## 2. Per-Query Breakdown Table\n",
        "| Query | Target Symbol | Dense Rank | BM25 Rank | Hybrid Rank |",
        "|---|---|:---:|:---:|:---:|",
    ])
    for r in records:
        md.append(f"| `{r['query']}` | `{r['expected']}` | {r['dense_rank']} | {r['bm25_rank']} | {r['hybrid_rank']} |")

    md.extend([
        "\n## 3. LaTeX Dissertation Table\n",
        "```latex",
        "\\begin{table}[h]",
        "\\centering",
        "\\begin{tabular}{lcccc}",
        "\\hline",
        "\\textbf{Retrieval Strategy} & \\textbf{Recall@1} & \\textbf{Recall@3} & \\textbf{Recall@5} & \\textbf{MRR} \\\\",
        "\\hline",
    ])
    for mode in ["dense", "bm25", "hybrid"]:
        s = summary[mode]
        r1 = f"{s['recall@1']:.2%}".replace("%", "\\%")
        r3 = f"{s['recall@3']:.2%}".replace("%", "\\%")
        r5 = f"{s['recall@5']:.2%}".replace("%", "\\%")
        mrr = f"{s['mrr']:.4f}"
        md.append(f"{mode.capitalize()} & {r1} & {r3} & {r5} & {mrr} \\\\")
    md.extend([
        "\\hline",
        "\\end{tabular}",
        "\\caption{Code Retrieval Performance across Dense, BM25, and Hybrid Fused Strategies.}",
        "\\label{tab:rag_retrieval_results}",
        "\\end{table}",
        "```\n",
    ])
    return "\n".join(md)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAG retrieval benchmark and generate academic reports.")
    parser.add_argument("--mock", action="store_true", help="Run with deterministic offline FakeEmbedder.")
    args = parser.parse_args()
    run_rag_eval(mock=args.mock)
