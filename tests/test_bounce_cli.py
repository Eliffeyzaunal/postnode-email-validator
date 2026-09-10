import json
from pathlib import Path

from app.bounce_classifier.cli import main


def test_cli_writes_safe_jsonl_and_unknown_report(tmp_path: Path):
    source = tmp_path / "events.jsonl"
    source.write_text(
        json.dumps({
            "event_id": "one",
            "recipient": "visible@example.com",
            "diagnostic_code": "550 5.1.1 visible@example.com user unknown",
        })
        + "\n"
        + json.dumps({"event_id": "two", "diagnostic_code": "599 new vendor response"})
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "classified.jsonl"
    report = tmp_path / "report.json"
    assert main([str(source), "--output", str(output), "--report", str(report)]) == 0
    output_text = output.read_text(encoding="utf-8")
    assert "visible@example.com" not in output_text
    rows = [json.loads(line) for line in output_text.splitlines()]
    assert [row["category"] for row in rows] == ["permanent_invalid_address", "unknown"]
    summary = json.loads(report.read_text(encoding="utf-8"))
    assert summary["unknown_rate"] == 0.5
    assert summary["top_unknown_patterns"] == [{"pattern": "599 new vendor response", "count": 1}]
