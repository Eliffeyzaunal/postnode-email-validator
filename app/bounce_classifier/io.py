import json
from pathlib import Path
from typing import Any


def read_events(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.casefold() == ".jsonl":
        events = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        payload = json.loads(text)
        events = payload if isinstance(payload, list) else [payload]
    if not all(isinstance(event, dict) for event in events):
        raise ValueError("Girdi bir JSON olay nesnesi veya JSON/JSONL olay listesi olmalidir.")
    return events


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
