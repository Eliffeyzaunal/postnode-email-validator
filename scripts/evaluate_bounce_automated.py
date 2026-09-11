from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.bounce_classifier.classifier import EventClassifier
from app.bounce_classifier.privacy import EMAIL_RE
from app.bounce_classifier.rules import rule_matches

REQUIRED_CATEGORIES = {
    "permanent_invalid_address",
    "mailbox_full",
    "temporary_server_error",
    "content_policy_rejection",
    "blocklist_rejection",
    "reputation_rate_limit",
    "automatic_response",
    "complaint",
    "unknown",
}


def safe_divide(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def load_dataset(path: Path) -> tuple[list[dict], bool]:
    text = path.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    if not rows:
        raise ValueError("Otomatik degerlendirme veri kumesi bos.")
    return rows, bool(EMAIL_RE.search(text))


def evaluate_automated(dataset: Path) -> dict:
    rows, clear_email_found = load_dataset(dataset)
    classifier = EventClassifier()

    expected_counts = Counter()
    predicted_counts = Counter()
    correct_by_category = Counter()
    confusion = Counter()
    errors = []
    permanence_total = Counter()
    permanence_correct = Counter()
    transient_as_permanent = 0

    for row in rows:
        event = row["event"]
        event_id = str(event["event_id"])
        expected = str(row["expected_category"])
        expected_permanence = str(row["expected_permanence"])

        result = classifier.classify(event)
        predicted = result.category.value
        predicted_permanence = result.permanence.value

        expected_counts[expected] += 1
        predicted_counts[predicted] += 1
        confusion[f"{expected}->{predicted}"] += 1

        if predicted == expected:
            correct_by_category[expected] += 1
        else:
            errors.append({
                "event_id": event_id,
                "expected": expected,
                "predicted": predicted,
                "rule_id": result.rule_id,
            })

        permanence_total[expected_permanence] += 1
        if predicted_permanence == expected_permanence:
            permanence_correct[expected_permanence] += 1
        if expected_permanence == "transient" and predicted_permanence == "permanent":
            transient_as_permanent += 1

    trigger_failures = []
    counter_failures = []

    for rule in classifier.rules:
        trigger_result = classifier.classify(rule.trigger_example)
        if trigger_result.rule_id != rule.rule_id or trigger_result.category != rule.category:
            trigger_failures.append({
                "rule_id": rule.rule_id,
                "selected_rule_id": trigger_result.rule_id,
                "expected_category": rule.category.value,
                "predicted_category": trigger_result.category.value,
            })

        counter_event = classifier.normalize(rule.counter_example)
        if rule_matches(rule, counter_event):
            counter_failures.append({"rule_id": rule.rule_id})

    total = len(rows)
    correct = sum(correct_by_category.values())
    accuracy = safe_divide(correct, total)
    categories_present = set(expected_counts)

    per_category = {
        category: {
            "count": count,
            "correct": correct_by_category[category],
            "recall": safe_divide(correct_by_category[category], count),
        }
        for category, count in sorted(expected_counts.items())
    }

    permanence = {
        label: {
            "count": count,
            "correct": permanence_correct[label],
            "accuracy": safe_divide(permanence_correct[label], count),
        }
        for label, count in sorted(permanence_total.items())
    }

    checks = {
        "dataset_size_at_least_300": total >= 300,
        "specification_accuracy_at_least_90_percent": accuracy >= 0.90,
        "all_required_categories_present": REQUIRED_CATEGORIES <= categories_present,
        "no_clear_email_in_dataset": not clear_email_found,
        "all_rule_trigger_examples_pass": not trigger_failures,
        "all_rule_counter_examples_pass": not counter_failures,
        "no_transient_event_classified_as_permanent": transient_as_permanent == 0,
    }

    return {
        "evaluation_type": "automated_synthetic_and_rule_fixture_validation",
        "dataset_size": total,
        "data_origin": "synthetic_anonymized_ses_like_events",
        "label_basis": "synthetic_specification",
        "specification_accuracy": accuracy,
        "category_counts": dict(sorted(expected_counts.items())),
        "predicted_counts": dict(sorted(predicted_counts.items())),
        "per_category": per_category,
        "confusion": dict(sorted(confusion.items())),
        "permanence": permanence,
        "transient_as_permanent_count": transient_as_permanent,
        "rule_fixture_validation": {
            "rule_count": len(classifier.rules),
            "trigger_failures": trigger_failures,
            "counter_failures": counter_failures,
        },
        "automated_acceptance": {
            **checks,
            "acceptance_met": all(checks.values()),
        },
        "customer_accuracy_claim": False,
        "errors": errors,
    }


def markdown_report(metrics: dict) -> str:
    acceptance = metrics["automated_acceptance"]
    fixture = metrics["rule_fixture_validation"]
    lines = [
        "# Gorev 4 Otomatik Degerlendirme Raporu",
        "",
        f"- Veri kumesi: **{metrics['dataset_size']}** anonim sentetik SES-benzeri olay",
        f"- Sentetik sartname uyumu: **%{metrics['specification_accuracy'] * 100:.2f}**",
        f"- Kural fixture sayisi: **{fixture['rule_count']}**",
        f"- Geciciyi kalici sayma: **{metrics['transient_as_permanent_count']}**",
        f"- Otomatik kabul: **{'GECTI' if acceptance['acceptance_met'] else 'KALDI'}**",
        "",
        "> Bu otomatik sentetik/fixture degerlendirmesidir. Gercek musteri veya uretim dogrulugu iddiasi degildir.",
        "",
        "## Otomatik kabul kontrolleri",
        "",
        "| Kontrol | Sonuc |",
        "|---|---|",
    ]
    for key, value in acceptance.items():
        if key == "acceptance_met":
            continue
        lines.append(f"| `{key}` | {'PASS' if value else 'FAIL'} |")

    lines.extend([
        "",
        "## Kategori sonuclari",
        "",
        "| Kategori | Ornek | Dogru | Recall |",
        "|---|---:|---:|---:|",
    ])
    for category, values in metrics["per_category"].items():
        lines.append(
            f"| `{category}` | {values['count']} | {values['correct']} | %{values['recall'] * 100:.2f} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gorev 4 icin otomatik sentetik ve kural-fixture degerlendirmesi."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evaluation/bounce-evaluation.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation/bounce-automated-results.json"),
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("evaluation/bounce-automated-report.md"),
    )
    parser.add_argument("--require-acceptance", action="store_true")
    args = parser.parse_args(argv)

    metrics = evaluate_automated(args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(markdown_report(metrics), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))

    if args.require_acceptance and not metrics["automated_acceptance"]["acceptance_met"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
