"""Evaluation runner to benchmark multi-agent coding performance."""
import argparse
import json
import os
import pathlib
import shutil
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.graph import run_task
from app.tools.files import apply_edits
from app.tools.sandbox import run_pytest


def parse_args():
    ap = argparse.ArgumentParser(description="MASEDA Evaluation Runner")
    ap.add_argument("--tasks", default=str(ROOT / "evaluation" / "tasks.json"), help="Path to tasks.json")
    ap.add_argument("--task-id", help="Run only a specific task ID")
    ap.add_argument("--limit", type=int, help="Limit number of tasks to execute")
    ap.add_argument(
        "--output",
        default=str(ROOT / "evaluation" / "results" / "baseline_results.json"),
        help="Path to save output results JSON",
    )
    ap.add_argument(
        "--report",
        default=str(ROOT / "evaluation" / "results" / "baseline_report.md"),
        help="Path to save Markdown/LaTeX evaluation report",
    )
    ap.add_argument(
        "--mock",
        action="store_true",
        help="Run in offline mock mode using golden solutions (0 API cost, instant test)",
    )
    return ap.parse_args()


def copy_repo(repo_rel: str) -> str:
    src = ROOT / repo_rel
    temp_dir = tempfile.mkdtemp(prefix="maseda_eval_")
    dest = os.path.join(temp_dir, "repo")
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache", "*.pyc"),
    )
    return dest


def run_single_task(task: dict, is_mock: bool = False) -> dict:
    repo_copy = copy_repo(task["repo"])
    t0 = time.time()

    # 1. Apply setup edits to initialize the problem state
    setup_edits = task.get("setup_edits", {})
    if setup_edits:
        apply_edits(repo_copy, setup_edits)

    # 2. Pre-check: verify tests fail initially
    pre_passed, pre_output = run_pytest(repo_copy, timeout=20)

    try:
        if is_mock:
            from app import llm

            plan = {"files": task["expected_files"], "steps": ["implement solution"]}
            golden = task.get("golden_solution", {})
            coder_res = {"edits": golden}
            rev_res = {"approved": True, "summary": "Looks good", "feedback": "Passes all tests", "suggested_fixes": []}

            replies = iter([plan, coder_res, rev_res])
            orig_complete = getattr(llm, "_complete", None)
            llm._complete = lambda s, u: (json.dumps(next(replies)), {"tokens": 120, "cost": 0.0003, "seconds": 0.1})
            try:
                res = run_task(task["instruction"], repo_copy)
            finally:
                if orig_complete:
                    llm._complete = orig_complete
        else:
            res = run_task(task["instruction"], repo_copy)

        return {
            "id": task["id"],
            "name": task["name"],
            "category": task.get("category", "general"),
            "pre_test_passed": pre_passed,
            "status": res.get("status", "failed"),
            "review_approved": res.get("review_approved", False),
            "iteration": res.get("iteration", 0),
            "total_tokens": res.get("total_tokens", 0),
            "total_cost": res.get("total_cost", 0.0),
            "total_seconds": res.get("total_seconds", round(time.time() - t0, 2)),
            "diff": res.get("diff", ""),
            "run_id": res.get("run_id", ""),
        }
    except Exception as e:
        return {
            "id": task["id"],
            "name": task["name"],
            "category": task.get("category", "general"),
            "pre_test_passed": pre_passed,
            "status": "failed",
            "review_approved": False,
            "iteration": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "total_seconds": round(time.time() - t0, 2),
            "error": str(e),
            "diff": "",
            "run_id": "",
        }
    finally:
        shutil.rmtree(os.path.dirname(repo_copy), ignore_errors=True)


def generate_reports(summary: dict, report_path: pathlib.Path):
    report_path.parent.mkdir(parents=True, exist_ok=True)
    cats = summary.get("categories", {})

    md_lines = [
        "# MASEDA Evaluation Benchmark Report",
        f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Overall Summary",
        f"- **Total Tasks:** {summary['total_tasks']}",
        f"- **Success Rate:** {summary['success_count']}/{summary['total_tasks']} ({summary['success_rate_pct']}%)",
        f"- **Total Cost:** ${summary['total_cost']:.4f}",
        f"- **Avg Tokens per Task:** {summary['avg_tokens']}",
        f"- **Avg Latency:** {summary['avg_seconds']:.2f}s",
        "",
        "## Performance by Task Category",
        "| Category | Tasks | Passed | Pass Rate (%) | Avg Rounds | Avg Tokens | Avg Time (s) |",
        "|---|---|---|---|---|---|---|",
    ]

    for cat_name, c in cats.items():
        md_lines.append(
            f"| {cat_name.title()} | {c['tasks']} | {c['passed']} | {c['pass_rate']}% | {c['avg_rounds']} | {c['avg_tokens']} | {c['avg_seconds']}s |"
        )

    md_lines.extend([
        "",
        "## LaTeX Table (Dissertation Ready)",
        "```latex",
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Baseline Multi-Agent Software Development Assistant (MASEDA) Performance}",
        r"\label{tab:baseline_performance}",
        r"\begin{tabular}{lcccccc}",
        r"\hline",
        r"\textbf{Category} & \textbf{Tasks} & \textbf{Passed} & \textbf{Pass Rate (\%)} & \textbf{Avg Rounds} & \textbf{Avg Tokens} & \textbf{Avg Time (s)} \\",
        r"\hline",
    ])

    for cat_name, c in cats.items():
        md_lines.append(
            f"{cat_name.replace('_', ' ').title():<18} & {c['tasks']:<5} & {c['passed']:<6} & {c['pass_rate']:<13} & {c['avg_rounds']:<10} & {c['avg_tokens']:<10} & {c['avg_seconds']:<12} \\\\"
        )

    md_lines.extend([
        r"\hline",
        f"\\textbf{{Total / Overall}} & {summary['total_tasks']:<5} & {summary['success_count']:<6} & {summary['success_rate_pct']:<13} & {summary.get('avg_rounds', 1.0):<10} & {summary['avg_tokens']:<10} & {summary['avg_seconds']:<12} \\\\",
        r"\hline",
        r"\end{tabular}",
        r"\end{table}",
        "```",
        "",
    ])

    report_path.write_text("\n".join(md_lines), encoding="utf-8")


def main():
    args = parse_args()
    tasks_path = pathlib.Path(args.tasks)
    if not tasks_path.exists():
        print(f"Error: tasks file not found at {tasks_path}")
        sys.exit(1)

    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    if args.task_id:
        tasks = [t for t in tasks if t["id"] == args.task_id]
        if not tasks:
            print(f"Error: task_id '{args.task_id}' not found.")
            sys.exit(1)

    if args.limit:
        tasks = tasks[: args.limit]

    mode_label = "MOCK (Offline)" if args.mock else "LIVE (Model)"
    print(f"Running evaluation benchmark on {len(tasks)} task(s) [{mode_label}]...")
    results = []
    out_path = pathlib.Path(args.output)
    report_path = pathlib.Path(args.report)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    for i, task in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] Starting {task['id']}: {task['name']} ({task.get('category')})...")
        r = run_single_task(task, is_mock=args.mock)
        results.append(r)
        status_icon = "[PASS]" if r["status"] == "success" else "[FAIL]"
        pre_icon = "[PRE:FAIL]" if not r["pre_test_passed"] else "[PRE:PASS]"
        print(
            f"[{i}/{len(tasks)}] {status_icon} Status: {r['status']} ({pre_icon}) | "
            f"Rounds: {r['iteration']} | Tokens: {r['total_tokens']} | Cost: ${r['total_cost']:.4f} | Time: {r['total_seconds']:.1f}s"
        )

        # Save checkpoint
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"tasks": results}, f, indent=2)

    # Compute aggregate metrics
    total = len(results)
    successes = sum(1 for r in results if r["status"] == "success")
    pass_rate = (successes / total * 100.0) if total > 0 else 0.0
    avg_tokens = (sum(r["total_tokens"] for r in results) / total) if total > 0 else 0
    total_cost = sum(r["total_cost"] for r in results)
    avg_seconds = (sum(r["total_seconds"] for r in results) / total) if total > 0 else 0.0
    avg_rounds = (sum(r["iteration"] for r in results) / total) if total > 0 else 0.0

    # Category breakdown
    categories = {}
    for cat in sorted(set(r["category"] for r in results)):
        cat_items = [r for r in results if r["category"] == cat]
        c_tot = len(cat_items)
        c_pass = sum(1 for r in cat_items if r["status"] == "success")
        categories[cat] = {
            "tasks": c_tot,
            "passed": c_pass,
            "pass_rate": round(c_pass / c_tot * 100.0, 1) if c_tot > 0 else 0.0,
            "avg_rounds": round(sum(r["iteration"] for r in cat_items) / c_tot, 2) if c_tot > 0 else 0.0,
            "avg_tokens": round(sum(r["total_tokens"] for r in cat_items) / c_tot, 1) if c_tot > 0 else 0,
            "avg_seconds": round(sum(r["total_seconds"] for r in cat_items) / c_tot, 2) if c_tot > 0 else 0.0,
        }

    summary = {
        "mode": mode_label,
        "total_tasks": total,
        "success_count": successes,
        "success_rate_pct": round(pass_rate, 2),
        "total_cost": round(total_cost, 4),
        "avg_tokens": round(avg_tokens, 1),
        "avg_rounds": round(avg_rounds, 2),
        "avg_seconds": round(avg_seconds, 2),
        "categories": categories,
        "results": results,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    generate_reports(summary, report_path)

    print("\n" + "=" * 65)
    print("                 EVALUATION BENCHMARK SUMMARY                 ")
    print("=" * 65)
    print(f"Mode:            {mode_label}")
    print(f"Total Tasks:     {total}")
    print(f"Success Rate:    {successes}/{total} ({pass_rate:.1f}%)")
    print(f"Total Cost:      ${total_cost:.4f}")
    print(f"Avg Tokens/Task: {avg_tokens:.1f}")
    print(f"Avg Rounds:      {avg_rounds:.2f}")
    print(f"Avg Latency:     {avg_seconds:.2f}s")
    print("-" * 65)
    print("Category Breakdown:")
    for cat_name, c in categories.items():
        print(f"  * {cat_name.title():<15}: {c['passed']}/{c['tasks']} ({c['pass_rate']}%) | {c['avg_tokens']} tokens | {c['avg_rounds']} rounds")
    print("=" * 65)
    print(f"Full JSON:   {out_path}")
    print(f"Report:      {report_path}\n")


if __name__ == "__main__":
    main()
