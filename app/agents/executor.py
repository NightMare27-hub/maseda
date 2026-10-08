from app.logger import log
from app.state import MAX_ITERS
from app.tools import sandbox
from app.tools.files import validate_python_syntax


def run_tests_node(state):
    edits = state.get("edits", {})
    it = state.get("iteration", 1)

    valid_syntax, syntax_err = validate_python_syntax(edits)
    if not valid_syntax:
        output = f"Syntax validation failed:\n{syntax_err}"
        log(state["run_id"], agent="run_tests", iteration=it, passed=False, output=output)
        return {"tests_passed": False, "test_output": output}

    passed, output = sandbox.run_tests(state["repo_path"], edits)
    log(state["run_id"], agent="run_tests", iteration=it, passed=passed, output=output[-1500:])
    return {"tests_passed": passed, "test_output": output}
