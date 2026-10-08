import json
import pathlib
import re
import time

LOG_DIR = pathlib.Path(__file__).resolve().parent.parent / "logs"
_SECRET = re.compile(r"(sk-[A-Za-z0-9_\-]{16,}|AIza[A-Za-z0-9_\-]{16,})")


def new_run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def redact(text: str) -> str:
    return _SECRET.sub("[REDACTED]", text)


def log(run_id: str, **event) -> None:
    """Append one JSON line to logs/<run_id>.jsonl. This file is our evaluation data."""
    LOG_DIR.mkdir(exist_ok=True)
    event["time"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    line = redact(json.dumps(event, ensure_ascii=False))
    with open(LOG_DIR / f"{run_id}.jsonl", "a", encoding="utf-8") as f:
        f.write(line + "\n")
