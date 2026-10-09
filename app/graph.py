from langgraph.graph import END, START, StateGraph

from app.agents import coder, planner, reviewer, run_tests_node
from app.logger import log, new_run_id
from app.state import State, route
from app.tools.files import make_diff


def build_graph():
    g = StateGraph(State)
    g.add_node("planner", planner)
    g.add_node("coder", coder)
    g.add_node("run_tests", run_tests_node)
    g.add_node("reviewer", reviewer)
    g.add_edge(START, "planner")
    g.add_edge("planner", "coder")
    g.add_edge("coder", "run_tests")
    g.add_edge("run_tests", "reviewer")
    g.add_conditional_edges("reviewer", route, {"coder": "coder", "end": END})
    return g.compile()


def _report_progress(node_name: str, update: dict):
    if node_name == "planner":
        plan = update.get("plan", {})
        approach = plan.get("approach")
        files = plan.get("files", [])
        print("\n[+] [PLANNER] Plan formulated:")
        if approach:
            print(f"    - Strategy: {approach}")
        if plan.get("operational_contract"):
            print(f"    - User Interface: {plan['operational_contract']}")
        print(f"    - Target files: {files}")
    elif node_name == "coder":
        edits = update.get("edits", {})
        print(f"\n[+] [CODER] Generated edits for: {list(edits.keys())}")
    elif node_name == "run_tests":
        passed = update.get("tests_passed", False)
        status = "PASSED (all tests green)" if passed else "FAILED (test failures detected)"
        print(f"[+] [SANDBOX] Test execution: {status}")
    elif node_name == "reviewer":
        approved = update.get("review_approved", False)
        it = update.get("iteration", 1)
        rf = update.get("reviewer_feedback", {})
        summary = rf.get("summary", "")
        verdict = "APPROVED" if approved else "REVISION REQUIRED"
        print(f"[+] [REVIEWER] Round {it} review: {verdict} - {summary}")


def run_task(
    task: str,
    repo_path: str,
    rag: bool = False,
    rag_mode: str = "hybrid",
    verbose: bool = True,
) -> dict:
    run_id = new_run_id()
    log(run_id, event="start", task=task, repo=repo_path, rag=rag, rag_mode=rag_mode)

    if verbose:
        print(f"\n[*] Starting MASEDA task: \"{task}\"")
        if rag:
            print(f"[*] RAG retrieval enabled (mode: {rag_mode})")

    initial_state = {
        "task": task,
        "repo_path": repo_path,
        "run_id": run_id,
        "rag_enabled": rag,
        "rag_mode": rag_mode,
        "retrieved_chunks": [],
        "total_tokens": 0,
        "total_cost": 0.0,
        "total_seconds": 0.0,
    }

    final = dict(initial_state)
    g = build_graph()
    for chunk in g.stream(initial_state):
        for node_name, node_update in chunk.items():
            final.update(node_update)
            if verbose:
                _report_progress(node_name, node_update)

    final["diff"] = make_diff(repo_path, final.get("edits", {}))
    log(
        run_id,
        event="end",
        status=final.get("status", "unknown"),
        iterations=final.get("iteration", 1),
        rag=rag,
        rag_mode=rag_mode,
        rag_chunks=len(final.get("retrieved_chunks", [])),
        total_tokens=final.get("total_tokens", 0),
        total_cost=final.get("total_cost", 0.0),
        total_seconds=final.get("total_seconds", 0.0),
    )
    return final
