"""Surgical patching engine for high-efficiency code editing without full-file rewrites."""
import re
from typing import Any, Tuple


def _normalize_newlines(text: str) -> str:
    """Normalize CRLF to LF for consistent block matching."""
    return text.replace("\r\n", "\n")


def _find_matching_block(content: str, search_block: str) -> Tuple[int, int]:
    """Find start and end character indices of search_block in content.

    Supports:
    1. Exact string match.
    2. Whitespace-normalized line matching (handles trailing spaces and minor indent drifts).
    Returns (start_idx, end_idx) or (-1, -1) if no match.
    """
    # 1. Direct exact match
    idx = content.find(search_block)
    if idx != -1:
        return idx, idx + len(search_block)

    # 2. Normalized line matching
    content_lines = content.split("\n")
    search_lines = search_block.split("\n")

    # Strip empty leading/trailing lines in search block for robust matching
    s_start = 0
    while s_start < len(search_lines) and not search_lines[s_start].strip():
        s_start += 1
    s_end = len(search_lines)
    while s_end > s_start and not search_lines[s_end - 1].strip():
        s_end -= 1

    clean_search = search_lines[s_start:s_end]
    if not clean_search:
        return -1, -1

    k = len(clean_search)
    match_start_line = -1

    for i in range(len(content_lines) - k + 1):
        window = content_lines[i : i + k]
        # Compare each line stripping trailing whitespace
        if all(w.rstrip() == s.rstrip() for w, s in zip(window, clean_search)):
            match_start_line = i
            break

    if match_start_line == -1:
        # Try stripping leading and trailing whitespace per line if indent changed
        for i in range(len(content_lines) - k + 1):
            window = content_lines[i : i + k]
            if all(w.strip() == s.strip() for w, s in zip(window, clean_search)):
                match_start_line = i
                break

    if match_start_line != -1:
        # Calculate character indices
        start_char = len("\n".join(content_lines[:match_start_line])) + (1 if match_start_line > 0 else 0)
        end_char = len("\n".join(content_lines[: match_start_line + k]))
        return start_char, end_char

    return -1, -1


def apply_surgical_patches(original_content: str, patches: list[dict[str, Any]]) -> Tuple[str, bool, str]:
    """Apply an ordered list of surgical search-and-replace patches to original_content.

    Each patch is expected to be:
    {"search": str, "replace": str}

    Returns:
        (updated_content, success_boolean, error_or_diagnostic_message)
    """
    if not patches:
        return original_content, True, "No patches provided."

    current = _normalize_newlines(original_content)

    for i, patch in enumerate(patches, 1):
        if not isinstance(patch, dict):
            return original_content, False, f"Patch #{i} is not a dictionary."

        search_str = _normalize_newlines(str(patch.get("search", "")))
        replace_str = _normalize_newlines(str(patch.get("replace", "")))

        if not search_str:
            return original_content, False, f"Patch #{i} contains an empty 'search' block."

        start_idx, end_idx = _find_matching_block(current, search_str)
        if start_idx == -1:
            preview = search_str.strip().split("\n")[0][:60]
            return (
                original_content,
                False,
                f"Patch #{i} failed: search block not found ('{preview}...').",
            )

        # Apply replacement
        current = current[:start_idx] + replace_str + current[end_idx:]

    return current, True, f"Successfully applied {len(patches)} surgical patch(es)."


def resolve_file_content(original_content: str, edit_spec: Any) -> Tuple[str, bool, str]:
    """Resolve an edit specification into complete file content.

    Supports:
    - Raw string (complete new file content).
    - Structured patch dict: {"mode": "patch", "patches": [...]}
    - Full content dict: {"mode": "full", "content": "..."}
    """
    if isinstance(edit_spec, str):
        return edit_spec, True, "Full content rewrite."

    if isinstance(edit_spec, dict):
        mode = edit_spec.get("mode", "full")
        if mode == "patch":
            patches = edit_spec.get("patches", [])
            return apply_surgical_patches(original_content, patches)
        if "content" in edit_spec:
            return str(edit_spec["content"]), True, "Full content extracted from dict."

    return original_content, False, f"Unrecognized edit specification type: {type(edit_spec)}."

