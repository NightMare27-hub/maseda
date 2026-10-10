"""Multi-file project scaffolding and dependency-ordered code synthesis engine."""
import ast
import pathlib
import re
from typing import Any, Tuple

from app.llm import ask_json
from app.logger import log
from app.tools.files import is_test_file, load_guidelines, safe_path


def get_file_tier(file_path: str) -> int:
    """Assign a priority tier (1 to 6) based on architectural layer. Lower numbers synthesized first."""
    name = pathlib.PurePosixPath(file_path).name.lower()

    # Tier 6: Test files always go last
    if is_test_file(file_path):
        return 6

    # Tier 1: Constants, exceptions, base types
    if any(k in name for k in ("const", "enum", "type", "error", "exception", "config", "setting")):
        return 1

    # Tier 2: Domain models, entities, data schemas
    if any(k in name for k in ("model", "schema", "entity", "dataclass", "item", "record")):
        return 2

    # Tier 3: Core primitives, math, utilities, helpers
    if any(k in name for k in ("util", "helper", "math", "string", "text", "collect", "geom", "valid")):
        return 3

    # Tier 4: Services, business logic, engines, storage, pipelines
    if any(k in name for k in ("service", "engine", "store", "db", "manager", "pipeline", "process", "repo")):
        return 4

    # Tier 5: CLI, API, UI, controllers, main entrypoints
    if any(k in name for k in ("main", "cli", "app", "api", "controller", "run", "entry")):
        return 5

    return 3  # Default middle tier


def sort_files_by_dependency(files: list[str]) -> list[str]:
    """Sort files topologically so foundations are built before dependent logic and tests."""
    return sorted(files, key=lambda f: (get_file_tier(f), f))


def extract_file_interfaces(code: str, file_path: str) -> str:
    """Extract class and function signatures using AST to propagate into downstream prompts."""
    try:
        tree = ast.parse(code)
    except Exception:
        return f"=== {file_path} (Raw AST unavailable) ==="

    lines = [f"=== EXPORTS & INTERFACES IN {file_path} ==="]
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
            base_str = f"({', '.join(bases)})" if bases else ""
            lines.append(f"class {node.name}{base_str}:")
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [a.arg for a in sub.args.args]
                    lines.append(f"    def {sub.name}({', '.join(args)}): ...")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            lines.append(f"def {node.name}({', '.join(args)}): ...")

    return "\n".join(lines)


SCAFFOLD_SYSTEM = """You are the Senior Modular Software Architect in MASEDA.
Your task is to synthesize a single specific Python file that fits into an overall multi-file architecture.

RULES:
1. Output ONLY a valid JSON object:
   {"edits": {"target/path.py": "complete new file content"}}
2. Write clean, complete, production-ready Python code with proper type annotations and docstrings.
3. Import and use the exact class and function interfaces already created in previous files (listed in INTERFACES AVAILABLE).
4. If this is a test file, write complete pytest tests asserting the behavior of previously created modules.
5. If this is a runnable CLI or script, provide a complete interactive entrypoint under `if __name__ == '__main__':`.
6. Prefer Python's Standard Library over external uninstalled packages.
7. Return ONLY valid JSON, no markdown fences or commentary."""


def synthesize_project_files(
    task: str,
    target_files: list[str],
    repo_path: str,
    run_id: str,
    rag_context: str = "",
) -> Tuple[dict[str, str], dict[str, Any]]:
    """Synthesize multiple files sequentially in topological dependency order.

    Propagates AST interfaces of completed files into subsequent file prompts to guarantee
    cross-module compatibility without hitting single-turn output token ceilings.
    """
    sorted_files = sort_files_by_dependency(target_files)
    accumulated_edits: dict[str, str] = {}
    interface_summaries: list[str] = []
    total_tokens = 0
    total_cost = 0.0
    total_seconds = 0.0

    guidelines = load_guidelines()
    guidelines_snippet = f"\n\nENGINEERING STANDARDS:\n{guidelines}" if guidelines else ""

    for idx, target_file in enumerate(sorted_files, 1):
        print(f"    [SCAFFOLD {idx}/{len(sorted_files)}] Synthesizing '{target_file}'...")

        interfaces_block = ""
        if interface_summaries:
            interfaces_block = (
                "\n\n=== PREVIOUSLY GENERATED MODULE INTERFACES (IMPORT & USE THESE) ===\n"
                + "\n\n".join(interface_summaries)
            )

        user_prompt = (
            f"OVERARCHING ARCHITECTURAL TASK:\n{task}\n\n"
            f"FULL TARGET FILE LIST:\n{sorted_files}\n\n"
            f"CURRENT FILE TO GENERATE ({idx}/{len(sorted_files)}):\n{target_file}\n"
            f"{rag_context}"
            f"{interfaces_block}"
            f"{guidelines_snippet}\n\n"
            f"Implement the complete, runnable Python code for '{target_file}'. "
            f"Ensure all imports match the module paths and names in the project."
        )

        data, meta = ask_json(SCAFFOLD_SYSTEM, user_prompt)
        total_tokens += meta.get("tokens", 0)
        total_cost += meta.get("cost", 0.0)
        total_seconds += meta.get("seconds", 0.0)

        # Extract file content
        file_content = ""
        edits = data.get("edits", {})
        if target_file in edits:
            file_content = str(edits[target_file])
        elif len(edits) == 1:
            file_content = str(next(iter(edits.values())))
        else:
            file_content = str(data.get("code", ""))

        if file_content:
            accumulated_edits[target_file] = file_content
            # Extract its interface for subsequent files
            if target_file.endswith(".py") and not is_test_file(target_file):
                interface_summaries.append(extract_file_interfaces(file_content, target_file))

        log(
            run_id,
            agent="scaffolder",
            file_index=idx,
            total_files=len(sorted_files),
            file=target_file,
            **meta,
        )

    return accumulated_edits, {
        "tokens": total_tokens,
        "cost": round(total_cost, 6),
        "seconds": round(total_seconds, 2),
    }

