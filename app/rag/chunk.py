import ast
import pathlib


def _lines(source: str, start: int, end: int) -> str:
    return "\n".join(source.splitlines()[start - 1:end])


def _docstring(node: ast.AST) -> str:
    value = ast.get_docstring(node)
    return f'    """{value}"""\n' if value else ""


def _class_signature(node: ast.ClassDef) -> str:
    bases = [ast.unparse(b) for b in node.bases]
    suffix = f"({', '.join(bases)})" if bases else ""
    return f"class {node.name}{suffix}:"


def _function_signature(node: ast.AST) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({ast.unparse(node.args)}):"


def _chunk(file: str, symbol: str, kind: str, parent: str, start: int, end: int, code: str) -> dict:
    chunk_id = f"{file}::{symbol}"
    return {
        "id": chunk_id,
        "file": file,
        "symbol": symbol,
        "kind": kind,
        "parent_class": parent,
        "start_line": start,
        "end_line": end,
        "code": code,
    }


def chunk_python_file(path: str | pathlib.Path, repo_root: str | pathlib.Path | None = None) -> list[dict]:
    p = pathlib.Path(path)
    root = pathlib.Path(repo_root) if repo_root else p.parent
    rel = p.resolve().relative_to(root.resolve()).as_posix()
    source = p.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        lines = source.splitlines()
        return [_chunk(rel, "module", "module", "", 1, max(1, len(lines)), source)]

    chunks = []

    module_nodes = (
        ast.Import,
        ast.ImportFrom,
        ast.Assign,
        ast.AnnAssign,
        ast.AugAssign,
    )
    selected = [n for n in tree.body if isinstance(n, module_nodes)]
    if selected:
        start = min(n.lineno for n in selected)
        end = max(getattr(n, "end_lineno", n.lineno) for n in selected)
        code = _lines(source, start, end)
    else:
        start = end = 1
        code = ""
    chunks.append(_chunk(rel, "module", "module", "", start, end, code))

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chunks.append(
                _chunk(
                    rel,
                    node.name,
                    "function",
                    "",
                    node.lineno,
                    node.end_lineno or node.lineno,
                    _lines(source, node.lineno, node.end_lineno or node.lineno),
                )
            )
        elif isinstance(node, ast.ClassDef):
            class_code = _lines(source, node.lineno, node.end_lineno or node.lineno)
            chunks.append(
                _chunk(
                    rel,
                    node.name,
                    "class",
                    "",
                    node.lineno,
                    node.end_lineno or node.lineno,
                    class_code,
                )
            )
            context = _class_signature(node) + "\n" + _docstring(node)
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_code = context + _lines(source, item.lineno, item.end_lineno or item.lineno)
                    chunks.append(
                        _chunk(
                            rel,
                            f"{node.name}.{item.name}",
                            "method",
                            node.name,
                            item.lineno,
                            item.end_lineno or item.lineno,
                            method_code,
                        )
                    )
    return chunks


def chunk_repo(repo_path: str | pathlib.Path, files: list[str] | None = None) -> list[dict]:
    root = pathlib.Path(repo_path)
    paths = [root / f for f in files] if files else sorted(root.rglob("*.py"))
    return [chunk for path in paths for chunk in chunk_python_file(path, root)]
