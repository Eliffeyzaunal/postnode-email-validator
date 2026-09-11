import json

import pytest

from app.bounce_classifier.io import read_events, write_jsonl


def test_read_events_supports_jsonl_and_ignores_blank_lines(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(
        json.dumps({"event_id": "one"})
        + "\n\n"
        + json.dumps({"event_id": "two"})
        + "\n",
        encoding="utf-8",
    )

    assert read_events(path) == [{"event_id": "one"}, {"event_id": "two"}]


def test_read_events_supports_json_list(tmp_path):
    path = tmp_path / "events.json"
    path.write_text(
        json.dumps([{"event_id": "one"}, {"event_id": "two"}]),
        encoding="utf-8",
    )

    assert read_events(path) == [{"event_id": "one"}, {"event_id": "two"}]


def test_read_events_wraps_single_json_object(tmp_path):
    path = tmp_path / "event.json"
    path.write_text(json.dumps({"event_id": "one"}), encoding="utf-8")

    assert read_events(path) == [{"event_id": "one"}]


@pytest.mark.parametrize(
    "payload",
    [
        ["not-an-object"],
        {"event_id": "ok"},
    ],
)
def test_read_events_rejects_non_object_events_only_when_present(tmp_path, payload):
    path = tmp_path / "bad.json"
    if isinstance(payload, dict):
        path.write_text(json.dumps(payload), encoding="utf-8")
        assert read_events(path) == [payload]
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValueError, match="JSON olay nesnesi"):
            read_events(path)


def test_write_jsonl_creates_parent_and_round_trips(tmp_path):
    path = tmp_path / "nested" / "out.jsonl"
    rows = [{"b": 2, "a": 1}, {"event_id": "two"}]

    write_jsonl(path, rows)

    assert path.exists()
    assert read_events(path) == rows
    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == '{"a": 1, "b": 2}'
