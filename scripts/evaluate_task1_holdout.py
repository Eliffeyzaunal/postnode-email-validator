"""Evaluate Task 1 on a frozen challenge set that is separate from acceptance data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.dns_checker import StaticDNSChecker
from app.models import DNSState
from app.repository import Repository
from app.validator import EmailValidatorService
from scripts.evaluate import classification_metrics, load_cases


DATASET_PATH = ROOT / "evaluation/task1-holdout.csv"
FROZEN_DATASET_SHA256 = "596bfc798839f00825c1e009b87db9bc188a7b3e327880c4fecdd607e8973b1f"
EXPECTED_SIZE = 300
EXPECTED_SUPPORT = {"gecerli": 100, "supheli": 100, "gecersiz": 100}


def dataset_sha256(path: Path) -> str:
    """Hash text identically on Windows and POSIX checkouts."""
    content = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(content).hexdigest()


def load_holdout(path: Path = DATASET_PATH) -> list[dict[str, str]]:
    digest = dataset_sha256(path)
    if digest != FROZEN_DATASET_SHA256:
        raise ValueError(
            "Holdout veri kümesi dondurulmuş SHA-256 değeriyle uyuşmuyor; "
            "sonuçları güncellemeden önce metodoloji incelemesi gerekir."
        )
    with path.open(encoding="utf-8", newline="") as stream:
        cases = list(csv.DictReader(stream))
    if len(cases) != EXPECTED_SIZE:
        raise ValueError(f"Holdout tam {EXPECTED_SIZE} satır içermelidir.")
    identifiers = [case["case_id"] for case in cases]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Holdout kimlikleri benzersiz olmalıdır.")
    support = Counter(case["expected_status"] for case in cases)
    if dict(support) != EXPECTED_SUPPORT:
        raise ValueError(f"Holdout sınıf dengesi değişti: {dict(support)}")
    acceptance_emails = {case["email"].strip().casefold() for case in load_cases()}
    overlap = [case["case_id"] for case in cases if case["email"].strip().casefold() in acceptance_emails]
    if overlap:
        raise ValueError(f"Kabul setiyle holdout çakışıyor: {overlap[:5]}")
    return cases


def _domain_for(case: dict[str, str]) -> str | None:
    if case["dns_state"] == "none":
        return None
    try:
        raw_domain = case["email"].strip().rsplit("@", 1)[1].rstrip(".")
        return raw_domain.encode("idna").decode("ascii").casefold()
    except (IndexError, UnicodeError):
        return None


def evaluate(cases: list[dict[str, str]]) -> dict:
    observations: list[tuple[str, str]] = []
    categories: list[str] = []
    failures: list[dict] = []
    with TemporaryDirectory(prefix="postnode-task1-holdout-") as directory:
        settings = Settings(
            _env_file=None,
            database_url=f"sqlite:///{Path(directory) / 'holdout.db'}",
        )
        repository = Repository(settings.database_url, settings.email_hash_secret)
        try:
            for case in cases:
                domain = _domain_for(case)
                states = {domain: DNSState(case["dns_state"])} if domain else {}
                service = EmailValidatorService(
                    settings,
                    repository,
                    StaticDNSChecker(states, default=DNSState.ERROR),
                )
                _, _, actual = service.validate_one(case["email"], persist=False)
                expected = case["expected_status"]
                observations.append((expected, actual.status.value))
                categories.append(case["category"])
                if expected != actual.status.value:
                    failures.append(
                        {
                            "case_id": case["case_id"],
                            "category": case["category"],
                            "expected": expected,
                            "actual": actual.status.value,
                            "reason_codes": [code.value for code in actual.reason_codes],
                        }
                    )
        finally:
            repository.close()

    confusion = Counter(observations)
    valid_total = sum(expected == "gecerli" for expected, _ in observations)
    false_nonvalid = sum(
        count
        for (expected, actual), count in confusion.items()
        if expected == "gecerli" and actual != "gecerli"
    )
    return {
        "evaluation_mode": "frozen_holdout",
        "dataset_size": len(cases),
        "dataset_sha256": FROZEN_DATASET_SHA256,
        "dns_mode": "static_scenarios",
        "data_origin": "mixed_external_reference_and_curated_adversarial",
        "class_balance": EXPECTED_SUPPORT,
        "acceptance_dataset_overlap": 0,
        "accuracy": round(sum(expected == actual for expected, actual in observations) / len(cases), 4),
        "false_positive_rate_valid_to_nonvalid": round(false_nonvalid / valid_total, 4),
        **classification_metrics(observations, categories),
        "origin_counts": dict(sorted(Counter(case["origin"] for case in cases).items())),
        "failures": failures,
        "limitations": [
            "Synthetic/curated addresses are used; there is no customer or SMTP RCPT TO data.",
            "The balanced class distribution is not an estimate of production prevalence.",
            "Static DNS scenarios measure decision logic; live DNS performance is reported separately.",
            "The corpus must remain frozen and must not be used to tune rules after results are recorded.",
        ],
    }


def write_markdown(report: dict, path: Path) -> None:
    class_rows = [
        f"| `{label}` | %{values['precision'] * 100:.2f} | %{values['recall'] * 100:.2f} | "
        f"%{values['f1'] * 100:.2f} | {values['support']} |"
        for label, values in report["per_class"].items()
    ]
    category_rows = [
        f"| `{category}` | {values['correct']}/{values['total']} | %{values['accuracy'] * 100:.2f} |"
        for category, values in report["category_success"].items()
    ]
    matrix = report["confusion_matrix"]
    lines = [
        "# Görev 1 Dondurulmuş Holdout Raporu",
        "",
        "Bu sonuç, 258 satırlık kabul/regresyon setinden ayrı ve sıfır satır örtüşmeli",
        "dondurulmuş challenge setinde ölçülmüştür. Veri müşteri trafiği değildir.",
        "",
        f"- Örnek: {report['dataset_size']} (her sınıfta 100)",
        f"- Accuracy: %{report['accuracy'] * 100:.2f}",
        f"- Macro precision: %{report['macro_average']['precision'] * 100:.2f}",
        f"- Macro recall: %{report['macro_average']['recall'] * 100:.2f}",
        f"- Macro F1: %{report['macro_average']['f1'] * 100:.2f}",
        f"- Geçerli → geçerli olmayan FPR: %{report['false_positive_rate_valid_to_nonvalid'] * 100:.2f}",
        f"- Yanlış sınıflandırma: {len(report['failures'])}",
        f"- Kabul seti örtüşmesi: {report['acceptance_dataset_overlap']}",
        f"- Dataset SHA-256: `{report['dataset_sha256']}`",
        "",
        "## Sınıf metrikleri",
        "",
        "| Sınıf | Precision | Recall | F1 | Destek |",
        "|---|---:|---:|---:|---:|",
        *class_rows,
        "",
        "## Confusion matrix",
        "",
        "| Beklenen \\ Üretilen | `gecerli` | `supheli` | `gecersiz` |",
        "|---|---:|---:|---:|",
        *[
            f"| `{expected}` | {matrix[expected]['gecerli']} | {matrix[expected]['supheli']} | "
            f"{matrix[expected]['gecersiz']} |"
            for expected in ("gecerli", "supheli", "gecersiz")
        ],
        "",
        "## Kategori bazlı başarı",
        "",
        "| Kategori | Doğru/Toplam | Başarı |",
        "|---|---:|---:|",
        *category_rows,
        "",
        "## Sınırlar",
        "",
        *[f"- {item}" for item in report["limitations"]],
        "",
        "Bu set kural geliştirmek için kullanılmaz. Bir hata bulunursa önce sonuç kayda alınır;",
        "düzeltmenin başarısı yeni bir holdout sürümüyle ölçülür.",
        "",
        "Yeniden üretim: `python scripts/evaluate_task1_holdout.py --output evaluation/task1-holdout-results.json --markdown evaluation/task1-holdout-report.md`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--min-accuracy", type=float, default=None)
    args = parser.parse_args()
    report = evaluate(load_holdout(args.dataset))
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    if args.markdown:
        write_markdown(report, args.markdown)
    print(output)
    if args.min_accuracy is not None and report["accuracy"] < args.min_accuracy:
        raise SystemExit(
            f"Holdout accuracy {report['accuracy']:.4f}, alt sınır {args.min_accuracy:.4f}."
        )


if __name__ == "__main__":
    main()
