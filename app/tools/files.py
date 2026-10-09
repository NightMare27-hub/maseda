import difflib
import pathlib

IGNORE_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", "chroma_db"}


def safe_path(repo: str, rel: str) -> pathlib.Path:
    """Resolve a relative path and refuse anything that escapes the repo folder."""
    root = pathlib.Path(repo).resolve()
    p = (root / rel).resolve()
    if pathlib.Path(rel).is_absolute() or root not in p.parents and p != root:
        raise ValueError(f"Unsafe path: {rel}")
    return p


def list_py_files(repo: str) -> list:
    root = pathlib.Path(repo).resolve()
    out = []
    for p in root.rglob("*.py"):
        rel = p.relative_to(root)
        if not (set(rel.parts) & IGNORE_DIRS):
            out.append(rel.as_posix())
    return sorted(out)


def read_file(repo: str, rel: str) -> str:
    return safe_path(repo, rel).read_text(encoding="utf-8")


def is_test_file(rel: str) -> bool:
    name = pathlib.PurePosixPath(rel).name
    return name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py"


def apply_edits(root: str, edits: dict) -> None:
    for rel, content in edits.items():
        p = safe_path(root, rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def make_diff(repo: str, edits: dict) -> str:
    chunks = []
    for rel, new in sorted(edits.items()):
        try:
            old = read_file(repo, rel)
        except FileNotFoundError:
            old = ""
        diff = difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile=f"a/{rel}", tofile=f"b/{rel}",
        )
        chunks.append("".join(diff))
    return "\n".join(c for c in chunks if c)


def validate_python_syntax(edits: dict) -> tuple[bool, str]:
    """Check Python files in edits for syntax errors using ast.parse."""
    import ast

    for rel, content in sorted(edits.items()):
        if rel.endswith(".py"):
            try:
                ast.parse(content, filename=rel)
            except SyntaxError as e:
                line_snippet = e.text.strip() if e.text else ""
                err = f"SyntaxError in {rel} at line {e.lineno}:{e.offset or 0}: {e.msg}"
                if line_snippet:
                    err += f"\n  {line_snippet}"
                return False, err
    return True, ""


def load_guidelines() -> str:
    """Load core engineering guidelines from docs/agent_guidelines.md."""
    base = pathlib.Path(__file__).resolve().parent.parent.parent
    path = base / "docs" / "agent_guidelines.md"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""

