import argparse

from app.graph import run_task
from app.tools.files import apply_edits


def main():
    ap = argparse.ArgumentParser(description="Multi-Agent Software Development Assistant")
    ap.add_argument("--repo", required=True, help="path to a Python repo")
    ap.add_argument("--task", required=True, help="what to do, in plain language")
    ap.add_argument("--apply", action="store_true", help="write the edits into the repo")
    ap.add_argument("--rag", action="store_true", help="enable AST-based RAG context retrieval")
    ap.add_argument(
        "--rag-mode",
        choices=["hybrid", "dense", "bm25"],
        default="hybrid",
        help="retrieval mode when --rag is active (default: hybrid)",
    )
    a = ap.parse_args()

    try:
        r = run_task(a.task, a.repo, rag=a.rag, rag_mode=a.rag_mode)
    except RuntimeError as e:
        raise SystemExit(f"ERROR: {e}")
    print("PLAN:", r["plan"])
    print("\nDIFF:\n" + (r["diff"] or "(no changes)"))
    print(f"\nSTATUS: {r['status']} after {r['iteration']} round(s). Run id: {r['run_id']}")
    if a.rag:
        chunk_count = len(r.get("retrieved_chunks", []))
        print(f"RAG: enabled ({a.rag_mode}) | {chunk_count} chunk(s) injected into context")
    rf = r.get("reviewer_feedback", {})
    if rf and rf.get("summary"):
        print(f"REVIEW: {rf['summary']}")
        if rf.get("feedback") and r["status"] != "success":
            print(f"DIAGNOSIS: {rf['feedback']}")

    user_exp = r.get("user_explanation") or rf.get("user_explanation")
    if user_exp:
        print("\n" + "=" * 60)
        print("EXPLANATION FOR USERS (PLAIN ENGLISH):")
        print(user_exp)
        print("=" * 60)

    tokens = r.get("total_tokens", 0)
    cost = r.get("total_cost", 0.0)
    seconds = r.get("total_seconds", 0.0)
    print(f"\nMETRICS: {tokens} tokens | ${cost:.4f} cost | {seconds:.2f}s elapsed")
    if a.apply and r["status"] == "success":
        apply_edits(a.repo, r["edits"])
        print("Edits applied to the repo. Review with git diff.")


if __name__ == "__main__":
    main()
