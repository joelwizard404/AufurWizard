from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


LOG_DIR  = Path.home() / ".aufur_wizard"
LOG_FILE = LOG_DIR / "history.log"


def log_operation(
    target: str,
    standard_id: str,
    standard_name: str,
    success: int,
    errors: int,
    bytes_wiped: int,
) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts":          datetime.now(timezone.utc).isoformat(),
        "target":      target,
        "standard_id": standard_id,
        "standard":    standard_name,
        "success":     success,
        "errors":      errors,
        "bytes_wiped": bytes_wiped,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def read_log(last_n: int = 50) -> list[dict]:
    if not LOG_FILE.exists():
        return []
    try:
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    entries = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
        if len(entries) >= last_n:
            break
    return entries
