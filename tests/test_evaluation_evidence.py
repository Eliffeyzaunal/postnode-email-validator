import csv

import pytest

from scripts.evaluate import (
    classification_metrics,
    evaluate,
    load_cases,
    prepare_review,
    review_summary,
)


def test_draft_labels_never_count_as_human_review(tmp_path):
    cases = load_cases()
    review = tmp_path / "review.csv"
    prepare_review(cases, review)
    summary = review_summary(cases, review)
    assert summary["confirmed"] == 0
    assert summary["pending"] == len(cases)
    assert summary["acceptance_met"] is False
    with pytest.raises(FileExistsError):
        prepare_review(cases, review)


def test_review_requires_identity_date_and_unchanged_case(tmp_path):
    cases = load_cases()[:2]
    review = tmp_path / "review.csv"
    prepare_review(cases, review)
    with review.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        rows = list(reader)
    rows[0].update(reviewed_status=cases[0]["expected_status"], reviewer="unit-test-reviewer", reviewed_at="2026-09-08")
    rows[1].update(reviewed_status="gecersiz", reviewer="unit-test-reviewer", reviewed_at="2026-09-08")
    with review.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = review_summary(cases, review)
    assert summary["confirmed"] == 1
    assert summary["disagreements"] == [cases[1]["id"]]
    changed = [dict(cases[0], email="changed@example.com"), cases[1]]
    assert review_summary(changed, review)["stale_reviews"] == [cases[0]["id"]]
    rows[0]["reviewer"] = ""
    with review.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="birlikte doldurulmalı"):
        review_summary(cases, review)


def test_evaluation_exposes_label_disagreement_instead_of_rewriting_it(tmp_path):
    case = dict(load_cases()[0], expected_status="gecersiz")
    report = evaluate([case], tmp_path / "not-reviewed.csv")
    assert report["accuracy"] == 0
    assert report["failures"][0]["case_id"] == case["id"]
    assert case["expected_status"] == "gecersiz"
    assert report["human_review"]["acceptance_met"] is False


def test_metrics_include_precision_recall_f1_matrix_and_categories():
    report = classification_metrics(
        [("gecerli", "gecerli"), ("supheli", "gecersiz"), ("gecersiz", "gecersiz")],
        ["syntax", "dns", "dns"],
    )
    assert report["per_class"]["gecerli"]["precision"] == 1.0
    assert report["per_class"]["supheli"]["recall"] == 0.0
    assert report["confusion_matrix"]["supheli"]["gecersiz"] == 1
    assert report["category_success"]["dns"] == {
        "correct": 1,
        "total": 2,
        "accuracy": 0.5,
    }
