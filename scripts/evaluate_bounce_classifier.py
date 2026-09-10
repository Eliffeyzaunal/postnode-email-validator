import argparse
import csv
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.bounce_classifier.classifier import EventClassifier
from app.bounce_classifier.models import EventCategory
from app.bounce_classifier.privacy import EMAIL_RE


def read_rows(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if EMAIL_RE.search(path.read_text(encoding="utf-8")):
        raise ValueError("Değerlendirme verisinde açık e-posta adresi bulundu.")
    return rows


def read_reviews(path: Path | None) -> dict[str, dict]:
    if not path or not path.exists():
        return {}
    reviews: dict[str, dict] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            event_id = row["event_id"]
            if event_id in reviews:
                raise ValueError(f"İnsan inceleme dosyasında yinelenen event_id: {event_id}")
            reviews[event_id] = row
    return reviews


def safe_divide(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def evaluate(dataset: Path, review: Path | None = None) -> tuple[dict, dict]:
    rows = read_rows(dataset)
    reviews = read_reviews(review)
    classifier = EventClassifier()
    confusion: Counter[str] = Counter()
    expected_counts: Counter[str] = Counter()
    predicted_counts: Counter[str] = Counter()
    correct_by_category: Counter[str] = Counter()
    unknown_patterns: Counter[str] = Counter()
    errors: list[dict] = []
    human_confirmed = 0
    human_correct = 0
    permanent_total = permanent_correct = 0
    transient_total = transient_correct = false_permanent = 0

    for row in rows:
        event_id = row["event"]["event_id"]
        review_row = reviews.get(event_id, {})
        reviewed = review_row.get("review_status", "").casefold() == "confirmed"
        human_label = review_row.get("human_category", "").strip()
        if reviewed and not human_label:
            raise ValueError(f"Onaylı satırda human_category boş: {event_id}")
        if reviewed and not review_row.get("reviewer", "").strip():
            raise ValueError(f"Onaylı satırda reviewer boş: {event_id}")
        if reviewed:
            reviewed_at = review_row.get("reviewed_at", "").strip()
            try:
                date.fromisoformat(reviewed_at)
            except ValueError as exc:
                raise ValueError(
                    f"Onaylı satırda reviewed_at ISO tarih değil: {event_id}"
                ) from exc
        expected = human_label if reviewed and human_label else row["expected_category"]
        if reviewed and human_label:
            EventCategory(human_label)
            human_confirmed += 1
        result = classifier.classify(row["event"])
        predicted = result.category.value
        expected_counts[expected] += 1
        predicted_counts[predicted] += 1
        confusion[f"{expected}->{predicted}"] += 1
        if predicted == expected:
            correct_by_category[expected] += 1
            if reviewed:
                human_correct += 1
        else:
            errors.append({"event_id": event_id, "expected": expected, "predicted": predicted, "rule_id": result.rule_id})
        expected_permanence = row["expected_permanence"]
        if expected_permanence == "permanent":
            permanent_total += 1
            permanent_correct += int(result.permanence.value == "permanent")
        elif expected_permanence == "transient":
            transient_total += 1
            transient_correct += int(result.permanence.value == "transient")
            false_permanent += int(result.permanence.value == "permanent")
        if result.category == EventCategory.UNKNOWN and result.unknown_pattern:
            unknown_patterns[result.unknown_pattern] += 1

    total = len(rows)
    dataset_ids = {row["event"]["event_id"] for row in rows}
    stale_review_ids = sorted(set(reviews) - dataset_ids)
    correct = sum(correct_by_category.values())
    per_category = {
        category: {
            "count": count,
            "correct": correct_by_category[category],
            "recall": safe_divide(correct_by_category[category], count),
        }
        for category, count in sorted(expected_counts.items())
    }
    metrics = {
        "dataset_size": total,
        "data_origin": "synthetic_anonymized_ses_like_events",
        "label_basis": "human_confirmed" if human_confirmed == total else "synthetic_specification_with_pending_human_review",
        "accuracy": safe_divide(correct, total),
        "category_counts": dict(sorted(expected_counts.items())),
        "predicted_counts": dict(sorted(predicted_counts.items())),
        "per_category": per_category,
        "confusion": dict(sorted(confusion.items())),
        "unknown_rate": safe_divide(predicted_counts[EventCategory.UNKNOWN.value], total),
        "permanence_metrics": {
            "permanent_examples": permanent_total,
            "permanent_recall": safe_divide(permanent_correct, permanent_total),
            "transient_examples": transient_total,
            "transient_recall": safe_divide(transient_correct, transient_total),
            "transient_as_permanent_count": false_permanent,
            "transient_as_permanent_rate": safe_divide(false_permanent, transient_total),
        },
        "human_review": {
            "confirmed": human_confirmed,
            "pending": total - human_confirmed,
            "minimum_required": 300,
            "accuracy": safe_divide(human_correct, human_confirmed),
            "stale_review_ids": stale_review_ids,
            "acceptance_met": (
                human_confirmed >= 300
                and safe_divide(human_correct, human_confirmed) >= 0.90
                and not stale_review_ids
            ),
        },
        "automated_checks": {
            "dataset_size_at_least_300": total >= 300,
            "draft_accuracy_at_least_90_percent": safe_divide(correct, total) >= 0.90,
            "no_clear_email_in_dataset": True,
        },
        "errors": errors,
    }
    unknown_report = {
        "dataset_size": total,
        "unknown_count": predicted_counts[EventCategory.UNKNOWN.value],
        "unknown_rate": metrics["unknown_rate"],
        "top_20_patterns": [
            {"pattern": pattern, "count": count}
            for pattern, count in unknown_patterns.most_common(20)
        ],
        "next_step": (
            "Her örüntüyü sağlayıcı ve gerçek teslim sonucu ile doğrula; tekrarlanan ve güvenilir "
            "olanlar için config/bounce_rules.json dosyasına kaynaklı kural, olumlu örnek ve karşı örnek ekle."
        ),
    }
    return metrics, unknown_report


def metrics_markdown(metrics: dict) -> str:
    permanence = metrics["permanence_metrics"]
    review = metrics["human_review"]
    lines = [
        "# Görev 4 Değerlendirme Raporu",
        "",
        f"- Veri kümesi: **{metrics['dataset_size']}** anonim sentetik SES-benzeri olay",
        f"- Taslak doğruluk: **%{metrics['accuracy'] * 100:.2f}**",
        f"- Bilinmeyen oranı: **%{metrics['unknown_rate'] * 100:.2f}**",
        f"- Kalıcı hata ayrımı geri çağırma: **%{permanence['permanent_recall'] * 100:.2f}**",
        f"- Geçici hata ayrımı geri çağırma: **%{permanence['transient_recall'] * 100:.2f}**",
        f"- Geçiciyi kalıcı sayma: **{permanence['transient_as_permanent_count']} / {permanence['transient_examples']}**",
        f"- İnsan incelemesi: **{review['confirmed']} onaylı, {review['pending']} bekliyor**",
        f"- İnsan etiketlerinde doğruluk: **%{review['accuracy'] * 100:.2f}**",
        "",
        "> Bu sonuç sentetik şartname etiketleriyle uyumu gösterir; gerçek müşteri doğruluğu değildir. "
        "En az 300 satır insan tarafından kontrol edilmeden Görev 4 insan-etiketli kabul kriteri tamamlanmış sayılmaz.",
        "",
        "## Kategori sonuçları",
        "",
        "| Kategori | Örnek | Doğru | Recall |",
        "|---|---:|---:|---:|",
    ]
    for category, values in metrics["per_category"].items():
        lines.append(f"| `{category}` | {values['count']} | {values['correct']} | %{values['recall'] * 100:.2f} |")
    return "\n".join(lines) + "\n"


def unknown_markdown(report: dict) -> str:
    lines = [
        "# Bilinmeyen Bounce Örüntüleri",
        "",
        f"- Bilinmeyen olay: **{report['unknown_count']} / {report['dataset_size']}**",
        f"- Oran: **%{report['unknown_rate'] * 100:.2f}**",
        "",
        "| Sıra | Güvenli örüntü | Adet |",
        "|---:|---|---:|",
    ]
    for index, item in enumerate(report["top_20_patterns"], 1):
        pattern = item["pattern"].replace("\\", "\\\\").replace("|", "\\|").replace("`", "\\`")
        lines.append(f"| {index} | `{pattern}` | {item['count']} |")
    lines.extend(["", "## Sonraki adım", "", report["next_step"], ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Görev 4 sınıflandırıcı ölçümlerini üretir.")
    parser.add_argument("--dataset", type=Path, default=Path("evaluation/bounce-evaluation.jsonl"))
    parser.add_argument("--review", type=Path, default=Path("evaluation/bounce-human-review.csv"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/bounce-results.json"))
    parser.add_argument("--markdown", type=Path, default=Path("evaluation/bounce-report.md"))
    parser.add_argument("--unknown-output", type=Path, default=Path("evaluation/bounce-unknown-patterns.json"))
    parser.add_argument("--unknown-markdown", type=Path, default=Path("evaluation/bounce-unknown-patterns.md"))
    parser.add_argument("--require-human-review", action="store_true")
    args = parser.parse_args(argv)
    metrics, unknown = evaluate(args.dataset, args.review)
    for path in (args.output, args.markdown, args.unknown_output, args.unknown_markdown):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(metrics_markdown(metrics), encoding="utf-8")
    args.unknown_output.write_text(json.dumps(unknown, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.unknown_markdown.write_text(unknown_markdown(unknown), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    if args.require_human_review and not metrics["human_review"]["acceptance_met"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
