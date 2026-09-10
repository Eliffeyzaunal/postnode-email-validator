"""Offline measurement with explicitly reviewable draft labels."""
import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.dns_checker import StaticDNSChecker
from app.models import DNSState, Status
from app.repository import Repository
from app.validator import EmailValidatorService


def load_cases() -> list[dict]:
    with (ROOT / "evaluation/evaluation.csv").open(encoding="utf-8", newline="") as stream:
        cases = [dict(row, id=f"core-{index:03d}", category="legacy_generated",
                      rationale="Önceki sentetik kümeden taslak etiket; bağımsız inceleme bekler.")
                 for index, row in enumerate(csv.DictReader(stream), 1)]
    specification = json.loads((ROOT / "evaluation/edge-cases.json").read_text(encoding="utf-8"))
    cases.extend(specification["cases"])
    for boundary in specification["boundaries"]:
        domain = ".".join("a" * length for length in boundary["domain_labels"])
        cases.append(dict(boundary, email="x" * boundary["local_length"] + "@" + domain,
                          dns_state="mx", category="length_boundary"))
    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Değerlendirme örneği kimlikleri benzersiz olmalıdır.")
    return cases


def case_digest(case: dict) -> str:
    fields = {key: case.get(key) for key in ("id", "email", "dns_state", "expected_status", "reason", "rationale")}
    return hashlib.sha256(json.dumps(fields, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def prepare_review(cases: list[dict], path: Path) -> None:
    """Never overwrite a person's existing decisions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, lineterminator="\n", fieldnames=[
            "case_id", "case_sha256", "email_json", "dns_state", "proposed_status", "rationale",
            "reviewed_status", "reviewer", "reviewed_at", "notes",
        ])
        writer.writeheader()
        for case in cases:
            writer.writerow(dict(case_id=case["id"], case_sha256=case_digest(case),
                                 email_json=json.dumps(case["email"], ensure_ascii=False), dns_state=case["dns_state"],
                                 proposed_status=case["expected_status"], rationale=case["rationale"]))


def review_summary(cases: list[dict], path: Path) -> dict:
    by_id = {case["id"]: case for case in cases}
    confirmed, disagreements, stale = [], [], []
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        seen = set()
        for row in rows:
            identifier = row.get("case_id", "")
            if identifier not in by_id or identifier in seen:
                raise ValueError(f"Bilinmeyen/tekrarlanan inceleme kimliği: {identifier}")
            seen.add(identifier)
            fields = [row.get(key, "").strip() for key in ("reviewed_status", "reviewer", "reviewed_at")]
            if not any(fields):
                continue
            if not all(fields):
                raise ValueError(f"Etiket, inceleyen ve tarih birlikte doldurulmalı: {identifier}")
            label, _reviewer, reviewed_at = fields
            Status(label)
            date.fromisoformat(reviewed_at)
            if row.get("case_sha256") != case_digest(by_id[identifier]):
                stale.append(identifier)
            elif label != by_id[identifier]["expected_status"]:
                disagreements.append(identifier)
            else:
                confirmed.append(identifier)
    return {
        "confirmed": len(confirmed), "pending": len(cases) - len(confirmed),
        "disagreements": disagreements, "stale_reviews": stale,
        "minimum_required": 200,
        "acceptance_met": len(confirmed) >= 200 and not disagreements and not stale,
    }


def list_scenarios() -> list[tuple[str, list[str], list[str], str | None]]:
    scenarios = [
        ("duplicate", ["person@example.com"] * 2, ["gecerli", "supheli"], "DUPLICATE_ADDRESS"),
        ("sequence-below-threshold", [f"lead{i}@example.com" for i in range(4)], ["gecerli"] * 4, None),
        ("sequence-at-threshold", [f"lead{i}@example.com" for i in range(5)], ["supheli"] * 5, "GENERATED_SEQUENCE"),
        ("sparse-numbers", [f"lead{i}@example.com" for i in [1, 10, 20, 30, 40]], ["gecerli"] * 5, None),
        ("concentration-below-minimum", [f"person{i}.sample@example.com" for i in range(99)], ["gecerli"] * 99, None),
    ]
    for common in (69, 70):
        emails = [f"person{i}.sample@shared.example" for i in range(common)]
        emails += [f"person@domain{i}.example" for i in range(100 - common)]
        labels = ["supheli" if common == 70 else "gecerli"] * common + ["gecerli"] * (100 - common)
        scenarios.append((f"concentration-{common}-percent", emails, labels,
                          "DOMAIN_CONCENTRATION" if common == 70 else None))
    return scenarios


def evaluate(cases: list[dict], review_path: Path) -> dict:
    observations, failures, batch_reports = [], [], []
    with TemporaryDirectory(prefix="postnode-evaluation-") as directory:
        settings = Settings(_env_file=None, database_url=f"sqlite:///{Path(directory) / 'evaluation.db'}")
        repository = Repository(settings.database_url, settings.email_hash_secret)
        try:
            for case in cases:
                states = {}
                if case["dns_state"] != "none":
                    try:
                        domain = case["email"].strip().rsplit("@", 1)[1].rstrip(".").encode("idna").decode("ascii").casefold()
                        states[domain] = DNSState(case["dns_state"])
                    except UnicodeError:
                        pass  # Invalid domain label: no DNS lookup should occur.
                service = EmailValidatorService(settings, repository, StaticDNSChecker(states, default=DNSState.ERROR))
                _, _, actual = service.validate_one(case["email"], persist=False)
                observations.append((case["expected_status"], actual.status.value))
                expected_reason = case.get("reason")
                if actual.status.value != case["expected_status"] or (
                    expected_reason and expected_reason not in actual.reason_codes
                ):
                    failures.append({"case_id": case["id"], "expected": case["expected_status"],
                                     "actual": actual.status.value, "reason_codes": list(actual.reason_codes)})
            service = EmailValidatorService(settings, repository, StaticDNSChecker({}))
            for identifier, emails, labels, reason in list_scenarios():
                _, _, actual = service.validate_many(emails, persist=False)
                correct = sum(item.status.value == label and (label != "supheli" or reason in item.reason_codes)
                              for item, label in zip(actual, labels, strict=True))
                batch_reports.append({"id": identifier, "size": len(emails), "correct": correct,
                                      "passed": correct == len(emails)})
        finally:
            repository.close()
    confusion = Counter(observations)
    valid_total = sum(wanted == "gecerli" for wanted, _ in observations)
    false_invalid = confusion[("gecerli", "gecersiz")]
    return {
        "dataset_size": len(cases), "dns_mode": "static", "data_origin": "synthetic",
        "labels": "proposed; human review tracked separately",
        "dataset_sha256": hashlib.sha256("".join(case_digest(case) for case in cases).encode()).hexdigest(),
        "accuracy": round(sum(wanted == actual for wanted, actual in observations) / len(cases), 4),
        "false_positive_rate_valid_to_invalid": round(false_invalid / valid_total, 4) if valid_total else None,
        "valid_examples": valid_total, "false_invalid_examples": false_invalid,
        "confusion": {f"{wanted}->{actual}": count for (wanted, actual), count in sorted(confusion.items())},
        "category_counts": dict(sorted(Counter(case["category"] for case in cases).items())),
        "failures": failures, "list_scenarios": batch_reports,
        "human_review": review_summary(cases, review_path),
        "scope": "Address cases run individually; list scenarios use default production thresholds. No real DNS or customer data.",
    }


def write_markdown(report: dict, path: Path) -> None:
    text = "\n".join([
        "# Değerlendirme Raporu", "",
        "Bu ölçüm sentetik veri ve sabit DNS cevaplarıyla üretilmiştir. Gerçek müşteri doğruluğu iddiası değildir.", "",
        f"- Adres örneği: {report['dataset_size']}",
        f"- Taslak etiketlere göre doğruluk: %{report['accuracy'] * 100:.2f}",
        f"- Geçerli → geçersiz: {report['false_invalid_examples']}/{report['valid_examples']}",
        f"- Liste senaryoları: {sum(item['passed'] for item in report['list_scenarios'])}/{len(report['list_scenarios'])} başarılı",
        f"- İnsan tarafından doğrulanmış etiket: {report['human_review']['confirmed']}",
        f"- İnsan incelemesi bekleyen: {report['human_review']['pending']}",
        f"- En az 200 insan onaylı etiket şartı: {'sağlandı' if report['human_review']['acceptance_met'] else 'henüz sağlanmadı'}", "",
        "Eski 200 üretilmiş örneğe farklı yazım, normalizasyon, DNS, rol, disposable ve uzunluk sınırı örnekleri eklenmiştir.",
        "Adresler tek tek ölçülür; yinelenme, ardışık üretim ve yoğunluk senaryoları ayrıca varsayılan eşiklerle ölçülür.",
        "Unicode/SMTPUTF8 yerel bölüm ve tırnaklı posta kutusu gibi destek kapsamı dışındaki biçimler bu ölçüme dahil değildir.", "",
        "İnsan incelemesi: `evaluation/human-review.csv` içindeki reviewed_status, reviewer ve reviewed_at alanlarını gerçek inceleyen doldurur.",
        "Çelişen veya değişmiş örneğe ait incelemeler otomatik onay sayılmaz. Ayrıntılar `evaluation/results.json` dosyasındadır.", "",
        "Yeniden üretim: `python scripts/evaluate.py --output evaluation/results.json --markdown evaluation/report.md`", "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--review", type=Path, default=ROOT / "evaluation/human-review.csv")
    parser.add_argument("--prepare-review", type=Path)
    parser.add_argument("--require-human-review", action="store_true")
    args = parser.parse_args()
    cases = load_cases()
    if args.prepare_review:
        prepare_review(cases, args.prepare_review)
        return
    report = evaluate(cases, args.review)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    if args.markdown:
        write_markdown(report, args.markdown)
    print(output)
    if report["failures"] or any(not item["passed"] for item in report["list_scenarios"]):
        raise SystemExit("Değerlendirme beklenen karar veya sebep koduyla uyuşmadı.")
    if args.require_human_review and not report["human_review"]["acceptance_met"]:
        raise SystemExit("En az 200 etiketin bağımsız insan incelemesi henüz tamamlanmadı.")


if __name__ == "__main__":
    main()
