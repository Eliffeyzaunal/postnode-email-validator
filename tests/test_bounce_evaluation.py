import csv
import json
from pathlib import Path

from app.config import PROJECT_ROOT
from scripts.evaluate_bounce_classifier import evaluate
from scripts.generate_bounce_evaluation import generate


def test_committed_bounce_dataset_is_deterministic_and_large_enough():
    path = PROJECT_ROOT / "evaluation" / "bounce-evaluation.jsonl"
    committed = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert committed == generate()
    assert len(committed) >= 300
    assert all("@" not in json.dumps(row, ensure_ascii=False) for row in committed)


def test_bounce_evaluation_meets_automated_thresholds_and_reports_safety():
    metrics, unknown = evaluate(
        PROJECT_ROOT / "evaluation" / "bounce-evaluation.jsonl",
        PROJECT_ROOT / "evaluation" / "bounce-human-review.csv",
    )
    assert metrics["dataset_size"] == 360
    assert metrics["accuracy"] >= 0.90
    assert metrics["permanence_metrics"]["permanent_recall"] >= 0.90
    assert metrics["permanence_metrics"]["transient_recall"] >= 0.90
    assert metrics["permanence_metrics"]["transient_as_permanent_count"] == 0
    assert metrics["human_review"] == {
        "confirmed": 0,
        "pending": 360,
        "minimum_required": 300,
        "accuracy": 0.0,
        "stale_review_ids": [],
        "acceptance_met": False,
    }
    assert unknown["unknown_count"] == 40
    assert 0 < len(unknown["top_20_patterns"]) <= 20
    assert unknown["next_step"]


def test_human_acceptance_uses_only_confirmed_labels(tmp_path: Path):
    source = PROJECT_ROOT / "evaluation" / "bounce-human-review.csv"
    with source.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    for row in rows[:300]:
        row["human_category"] = row["proposed_category"]
        row["review_status"] = "confirmed"
        row["reviewer"] = "Test Reviewer"
        row["reviewed_at"] = "2026-09-10"
    review = tmp_path / "review.csv"
    with review.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    metrics, _ = evaluate(PROJECT_ROOT / "evaluation" / "bounce-evaluation.jsonl", review)
    assert metrics["human_review"]["confirmed"] == 300
    assert metrics["human_review"]["accuracy"] == 1.0
    assert metrics["human_review"]["acceptance_met"] is True
