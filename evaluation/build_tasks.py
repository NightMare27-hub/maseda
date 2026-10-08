import json
import pathlib

root = pathlib.Path(__file__).resolve().parent.parent

math_code = (root / "evaluation/bench_repo/math_utils.py").read_text(encoding="utf-8")
text_code = (root / "evaluation/bench_repo/text_utils.py").read_text(encoding="utf-8")
coll_code = (root / "evaluation/bench_repo/collection_utils.py").read_text(encoding="utf-8")
geom_code = (root / "evaluation/bench_repo/geometry.py").read_text(encoding="utf-8")
val_code = (root / "evaluation/bench_repo/validator.py").read_text(encoding="utf-8")
calc_code = (root / "evaluation/toy_repo/calculator.py").read_text(encoding="utf-8")

good_calc = """def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def power(base, exp):
    return base ** exp
"""

tasks = [
    {
        "id": "task_01",
        "name": "calculator_divide",
        "repo": "evaluation/toy_repo",
        "category": "bugfix",
        "instruction": "Implement divide(a, b) in calculator.py. It must return a / b and raise ValueError with a clear message when b is zero.",
        "expected_files": ["calculator.py"],
        "setup_edits": {},
        "golden_solution": {"calculator.py": good_calc},
    },
    {
        "id": "task_02",
        "name": "math_power",
        "repo": "evaluation/bench_repo",
        "category": "feature",
        "instruction": "Implement power(base, exp) in math_utils.py. It must compute base raised to exp (base ** exp).",
        "expected_files": ["math_utils.py"],
        "setup_edits": {"math_utils.py": math_code.replace("def power(base, exp):\n    return base ** exp", "")},
        "golden_solution": {"math_utils.py": math_code},
    },
    {
        "id": "task_03",
        "name": "math_factorial",
        "repo": "evaluation/bench_repo",
        "category": "bugfix",
        "instruction": "Ensure factorial(n) in math_utils.py correctly handles n == 0 by returning 1, returns n! for positive integers, and raises ValueError for negative inputs.",
        "expected_files": ["math_utils.py"],
        "setup_edits": {
            "math_utils.py": math_code.replace(
                'if n < 0:\n        raise ValueError("Factorial not defined for negative numbers")',
                "# buggy: no negative check",
            )
        },
        "golden_solution": {"math_utils.py": math_code},
    },
    {
        "id": "task_04",
        "name": "math_is_prime",
        "repo": "evaluation/bench_repo",
        "category": "feature",
        "instruction": "Implement is_prime(n) in math_utils.py returning True if n is a prime number, and False for n <= 1 or composite numbers.",
        "expected_files": ["math_utils.py"],
        "setup_edits": {
            "math_utils.py": math_code.replace(
                "def is_prime(n):", 'def is_prime(n):\n    return False\n    _x = """'
            ).replace(
                'return True\n\n\ndef fibonacci', 'return True"""\n\n\ndef fibonacci'
            )
        },
        "golden_solution": {"math_utils.py": math_code},
    },
    {
        "id": "task_05",
        "name": "math_fibonacci",
        "repo": "evaluation/bench_repo",
        "category": "feature",
        "instruction": "Implement fibonacci(n) in math_utils.py returning the n-th Fibonacci number with 0-indexing (fib(0)=0, fib(1)=1), raising ValueError for negative numbers.",
        "expected_files": ["math_utils.py"],
        "setup_edits": {
            "math_utils.py": math_code.replace(
                "def fibonacci(n):", 'def fibonacci(n):\n    return 0\n    _x = """'
            ).replace('return b\n\n\ndef clamp', 'return b"""\n\n\ndef clamp')
        },
        "golden_solution": {"math_utils.py": math_code},
    },
    {
        "id": "task_06",
        "name": "math_clamp",
        "repo": "evaluation/bench_repo",
        "category": "edge_case",
        "instruction": "Implement clamp(val, min_val, max_val) in math_utils.py returning min_val if val < min_val, max_val if val > max_val, and val otherwise. Raise ValueError if min_val > max_val.",
        "expected_files": ["math_utils.py"],
        "setup_edits": {
            "math_utils.py": math_code.replace(
                "def clamp(val, min_val, max_val):",
                'def clamp(val, min_val, max_val):\n    return val\n    _x = """',
            )
            + '"""\n'
        },
        "golden_solution": {"math_utils.py": math_code},
    },
    {
        "id": "task_07",
        "name": "text_truncate",
        "repo": "evaluation/bench_repo",
        "category": "bugfix",
        "instruction": "Fix truncate(text, max_len, suffix='...') in text_utils.py so it returns the original text unmodified if len(text) <= max_len.",
        "expected_files": ["text_utils.py"],
        "setup_edits": {
            "text_utils.py": text_code.replace(
                "if len(text) <= max_len:\n        return text",
                "# bug: missing length check",
            )
        },
        "golden_solution": {"text_utils.py": text_code},
    },
    {
        "id": "task_08",
        "name": "text_slugify",
        "repo": "evaluation/bench_repo",
        "category": "feature",
        "instruction": "Implement slugify(text) in text_utils.py to convert text to lowercase, remove punctuation, replace whitespace with single hyphens, and strip leading/trailing hyphens.",
        "expected_files": ["text_utils.py"],
        "setup_edits": {
            "text_utils.py": text_code.replace(
                "def slugify(text: str) -> str:",
                'def slugify(text: str) -> str:\n    return ""\n    _x = """',
            ).replace(
                'return text.strip("-")\n\n\ndef count_words',
                'return text.strip("-")"""\n\n\ndef count_words',
            )
        },
        "golden_solution": {"text_utils.py": text_code},
    },
    {
        "id": "task_09",
        "name": "text_count_words",
        "repo": "evaluation/bench_repo",
        "category": "feature",
        "instruction": "Implement count_words(text) in text_utils.py returning a dictionary mapping lowercase words to their occurrences, ignoring punctuation.",
        "expected_files": ["text_utils.py"],
        "setup_edits": {
            "text_utils.py": text_code.replace(
                "def count_words(text: str) -> dict:",
                'def count_words(text: str) -> dict:\n    return {}\n    _x = """',
            ).replace(
                "return counts\n\n\ndef capitalize_words",
                'return counts"""\n\n\ndef capitalize_words',
            )
        },
        "golden_solution": {"text_utils.py": text_code},
    },
    {
        "id": "task_10",
        "name": "text_capitalize_words",
        "repo": "evaluation/bench_repo",
        "category": "edge_case",
        "instruction": "Implement capitalize_words(text) in text_utils.py capitalizing each word while preserving original space characters between words.",
        "expected_files": ["text_utils.py"],
        "setup_edits": {
            "text_utils.py": text_code.replace(
                'return " ".join(word.capitalize() for word in text.split(" "))',
                "return text.title()",
            )
        },
        "golden_solution": {"text_utils.py": text_code},
    },
    {
        "id": "task_11",
        "name": "collection_chunk_list",
        "repo": "evaluation/bench_repo",
        "category": "bugfix",
        "instruction": "Implement chunk_list(lst, size) in collection_utils.py splitting lst into sublists of length size. Raise ValueError if size <= 0.",
        "expected_files": ["collection_utils.py"],
        "setup_edits": {
            "collection_utils.py": coll_code.replace(
                'if size <= 0:\n        raise ValueError("Chunk size must be positive")',
                "# bug: missing non-positive size check",
            )
        },
        "golden_solution": {"collection_utils.py": coll_code},
    },
    {
        "id": "task_12",
        "name": "collection_flatten",
        "repo": "evaluation/bench_repo",
        "category": "feature",
        "instruction": "Implement flatten(nested_list) in collection_utils.py recursively flattening arbitrarily nested lists into a flat list.",
        "expected_files": ["collection_utils.py"],
        "setup_edits": {
            "collection_utils.py": coll_code.replace(
                "def flatten(nested_list: list) -> list:",
                'def flatten(nested_list: list) -> list:\n    return nested_list\n    _x = """',
            ).replace(
                "return out\n\n\ndef deduplicate", 'return out"""\n\n\ndef deduplicate'
            )
        },
        "golden_solution": {"collection_utils.py": coll_code},
    },
    {
        "id": "task_13",
        "name": "collection_deduplicate",
        "repo": "evaluation/bench_repo",
        "category": "feature",
        "instruction": "Implement deduplicate(items) in collection_utils.py returning a list of elements with duplicates removed while preserving insertion order.",
        "expected_files": ["collection_utils.py"],
        "setup_edits": {
            "collection_utils.py": coll_code.replace(
                "def deduplicate(items: list) -> list:",
                'def deduplicate(items: list) -> list:\n    return list(set(items))\n    _x = """',
            ).replace(
                "return out\n\n\ndef find_first", 'return out"""\n\n\ndef find_first'
            )
        },
        "golden_solution": {"collection_utils.py": coll_code},
    },
    {
        "id": "task_14",
        "name": "collection_find_first",
        "repo": "evaluation/bench_repo",
        "category": "edge_case",
        "instruction": "Implement find_first(predicate, iterable, default=None) in collection_utils.py returning the first item where predicate(item) is True, or default if none match.",
        "expected_files": ["collection_utils.py"],
        "setup_edits": {
            "collection_utils.py": coll_code.replace(
                "def find_first(predicate, iterable, default=None):",
                'def find_first(predicate, iterable, default=None):\n    return None\n    _x = """',
            )
            + '"""\n'
        },
        "golden_solution": {"collection_utils.py": coll_code},
    },
    {
        "id": "task_15",
        "name": "geometry_distance",
        "repo": "evaluation/bench_repo",
        "category": "feature",
        "instruction": "Implement distance(p1, p2) in geometry.py calculating the Euclidean distance between two 2D points represented as (x, y) tuples.",
        "expected_files": ["geometry.py"],
        "setup_edits": {
            "geometry.py": geom_code.replace(
                "return math.hypot(p1[0] - p2[0], p1[1] - p2[1])", "return 0.0"
            )
        },
        "golden_solution": {"geometry.py": geom_code},
    },
    {
        "id": "task_16",
        "name": "geometry_rectangle",
        "repo": "evaluation/bench_repo",
        "category": "feature",
        "instruction": "Implement Rectangle(width, height) class in geometry.py with area() and perimeter() methods, raising ValueError if width or height is negative.",
        "expected_files": ["geometry.py"],
        "setup_edits": {
            "geometry.py": geom_code.replace(
                "class Rectangle:", 'class DummyRect:\n    _x = """'
            ).replace(
                "return 2 * (self.width + self.height)\n\n\ndef is_inside_box",
                'return 0"""\n\n\ndef is_inside_box',
            )
        },
        "golden_solution": {"geometry.py": geom_code},
    },
    {
        "id": "task_17",
        "name": "geometry_is_inside_box",
        "repo": "evaluation/bench_repo",
        "category": "edge_case",
        "instruction": "Implement is_inside_box(point, box) in geometry.py checking whether point (x, y) is inside or on the boundary of box (x1, y1, x2, y2).",
        "expected_files": ["geometry.py"],
        "setup_edits": {
            "geometry.py": geom_code.replace(
                "return x1 <= x <= x2 and y1 <= y <= y2", "return False"
            )
        },
        "golden_solution": {"geometry.py": geom_code},
    },
    {
        "id": "task_18",
        "name": "validator_validate_email",
        "repo": "evaluation/bench_repo",
        "category": "feature",
        "instruction": "Implement validate_email(email) in validator.py checking whether email has a valid username, @ symbol, and domain extension.",
        "expected_files": ["validator.py"],
        "setup_edits": {
            "validator.py": val_code.replace(
                "return bool(re.match(pattern, email.strip()))", "return False"
            )
        },
        "golden_solution": {"validator.py": val_code},
    },
    {
        "id": "task_19",
        "name": "geometry_scale_rectangle_cross_module",
        "repo": "evaluation/bench_repo",
        "category": "multi_file",
        "instruction": "Implement scale_rectangle(rect, factor) in geometry.py importing and using clamp from math_utils.py to ensure the scaling factor is clamped between 0.1 and 10.0.",
        "expected_files": ["geometry.py"],
        "setup_edits": {
            "geometry.py": geom_code.replace(
                "def scale_rectangle(rect: Rectangle, factor: float) -> Rectangle:\n    safe_factor = clamp(factor, 0.1, 10.0)\n    return Rectangle(rect.width * safe_factor, rect.height * safe_factor)",
                "def scale_rectangle(rect, factor):\n    return rect",
            )
        },
        "golden_solution": {"geometry.py": geom_code},
    },
    {
        "id": "task_20",
        "name": "validator_validate_slug_cross_module",
        "repo": "evaluation/bench_repo",
        "category": "multi_file",
        "instruction": "Implement validate_slug(text) in validator.py importing and using slugify from text_utils.py to verify if text is non-empty and matches its slugified version.",
        "expected_files": ["validator.py"],
        "setup_edits": {
            "validator.py": val_code.replace(
                "def validate_slug(text: str) -> bool:\n    return slugify(text) == text and len(text) > 0",
                "def validate_slug(text: str) -> bool:\n    return False",
            )
        },
        "golden_solution": {"validator.py": val_code},
    },
]

out = root / "evaluation/tasks.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(tasks, f, indent=2)

print(f"Generated {len(tasks)} tasks into {out}")
