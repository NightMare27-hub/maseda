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


def run_task(task: str, repo_path: str) -> dict:
    run_id = new_run_id()
    log(run_id, event="start", task=task, repo=repo_path)
    final = build_graph().invoke({
        "task": task,
        "repo_path": repo_path,
        "run_id": run_id,
        "total_tokens": 0,
        "total_cost": 0.0,
        "total_seconds": 0.0,
    })
    final["diff"] = make_diff(repo_path, final.get("edits", {}))
    log(
        run_id,
        event="end",
        status=final["status"],
        iterations=final["iteration"],
        total_tokens=final.get("total_tokens", 0),
        total_cost=final.get("total_cost", 0.0),
        total_seconds=final.get("total_seconds", 0.0),
    )
    return final
