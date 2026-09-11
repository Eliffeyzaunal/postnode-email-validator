"""Evaluate Task 1 with independent strict syntax and a shared live DNS snapshot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import dns.resolver
from email_validator import EmailNotValidError, validate_email

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.dns_checker import DNSChecker, StaticDNSChecker
from app.models import DNSState
from app.reason_codes import ReasonCode
from app.repository import Repository
from app.syntax import validate_syntax
from app.validator import EmailValidatorService
from scripts.evaluate import classification_metrics


DATASET_PATH = ROOT / "evaluation/task1-live-challenge.csv"
FROZEN_DATASET_SHA256 = "c3cd5673d6cdf29dd2f611cb4f70a17aee52c76d62d268112e06e822cb01939e"
EXPECTED_SIZE = 200
RISK_CATEGORIES = {"role_account", "disposable_domain", "provider_typo", "smtputf8"}


def dataset_sha256(path: Path) -> str:
    """Hash text identically on Windows and POSIX checkouts."""
    content = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(content).hexdigest()


def load_cases(path: Path = DATASET_PATH) -> list[dict[str, str]]:
    digest = dataset_sha256(path)
    if digest != FROZEN_DATASET_SHA256:
        raise ValueError("Live challenge corpus SHA-256 değeriyle uyuşmuyor.")
    with path.open(encoding="utf-8", newline="") as stream:
        cases = list(csv.DictReader(stream))
    if len(cases) != EXPECTED_SIZE:
        raise ValueError(f"Live challenge tam {EXPECTED_SIZE} satır içermelidir.")
    if len({case["case_id"] for case in cases}) != EXPECTED_SIZE:
        raise ValueError("Live challenge kimlikleri benzersiz olmalıdır.")
    if any(
        case["risk_if_deliverable"] not in RISK_CATEGORIES | {"none"}
        for case in cases
    ):
        raise ValueError("Bilinmeyen risk_if_deliverable değeri bulundu.")
    return cases


def reference_decision(
    email: str,
    risk_if_deliverable: str,
    dns_state: DNSState | None,
) -> tuple[str | None, str]:
    """Return a three-class label from strict syntax and one live DNS snapshot.

    The external package is the independent syntax oracle. The same captured
    DNS state is used for both the expected decision and the project run so a
    transient resolver difference cannot bias either side.
    """
    options = {
        "allow_smtputf8": True,
        "allow_quoted_local": False,
        "allow_domain_literal": False,
        "allow_display_name": False,
        "globally_deliverable": True,
        "strict": True,
    }
    try:
        validate_email(email, check_deliverability=False, **options)
    except EmailNotValidError:
        return "gecersiz", "independent_strict_syntax"

    if dns_state is None or dns_state == DNSState.ERROR:
        return None, "shared_live_dns_unknown"
    if dns_state in {DNSState.NXDOMAIN, DNSState.NO_MAIL_HOST}:
        return "gecersiz", f"shared_live_dns_{dns_state.value}"
    if risk_if_deliverable == "none":
        return "gecerli", f"shared_live_dns_{dns_state.value}"
    return "supheli", f"shared_live_dns_{dns_state.value}+{risk_if_deliverable}"


def project_domain(email: str) -> str | None:
    result = validate_syntax(email, allow_smtputf8=True)
    return result.domain if result.valid else None


def probe_nameservers(
    requested: list[str] | None,
    timeout_seconds: float,
) -> tuple[list[str], list[dict]]:
    """Select responsive configured resolvers without silently adding public DNS."""
    configured = list(requested or dns.resolver.Resolver(configure=True).nameservers)
    probes: list[dict] = []
    for nameserver in configured:
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [nameserver]
        resolver.timeout = min(timeout_seconds, 2.0)
        resolver.lifetime = min(timeout_seconds, 2.0)
        started = time.perf_counter()
        try:
            answer = resolver.resolve("gmail.com", "MX")
            success = bool(answer)
            error = None
        except dns.exception.DNSException as exc:
            success = False
            error = type(exc).__name__
        probes.append(
            {
                "nameserver": nameserver,
                "success": success,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "error": error,
            }
        )
    responsive = [item["nameserver"] for item in probes if item["success"]]
    return responsive or configured, probes


def resolve_dns_snapshot(
    domains: set[str],
    checkers: list[tuple[str, DNSChecker]],
    retries: int,
) -> tuple[dict[str, DNSState], dict]:
    """Resolve unique domains with explicit per-resolver failover.

    A technical DNS error from one resolver is not accepted as the final state while
    another explicitly configured resolver is available. Each round tries every
    responsive resolver; only technical errors are retried. NXDOMAIN, NO_MAIL_HOST,
    MX and A_FALLBACK are terminal because they are actual DNS outcomes.
    """
    if not checkers:
        raise ValueError("Canli DNS snapshot icin en az bir resolver gereklidir.")

    states: dict[str, DNSState] = {}
    attempts: dict[str, int] = {}
    details: dict[str, str | None] = {}
    resolved_via: dict[str, str | None] = {}
    resolver_attempts: dict[str, list[dict[str, str | int | None]]] = {}
    ordered = sorted(domains)

    for index, domain in enumerate(ordered, 1):
        result = None
        selected_nameserver: str | None = None
        trace: list[dict[str, str | int | None]] = []
        total_attempts = 0

        for round_number in range(1, retries + 2):
            for nameserver, checker in checkers:
                total_attempts += 1
                candidate = checker._lookup_uncached(domain)
                trace.append(
                    {
                        "round": round_number,
                        "nameserver": nameserver,
                        "state": candidate.state.value,
                        "detail": candidate.detail,
                    }
                )
                result = candidate
                if candidate.state != DNSState.ERROR:
                    selected_nameserver = nameserver
                    break
            if result is not None and result.state != DNSState.ERROR:
                break

        assert result is not None
        states[domain] = result.state
        attempts[domain] = total_attempts
        details[domain] = result.detail
        resolved_via[domain] = selected_nameserver
        resolver_attempts[domain] = trace

        if index % 10 == 0 or index == len(ordered):
            print(f"DNS snapshot: {index}/{len(ordered)} domain", file=sys.stderr)

    state_counts = Counter(state.value for state in states.values())
    technical_errors = [domain for domain, state in states.items() if state == DNSState.ERROR]
    return states, {
        "domain_count": len(ordered),
        "state_counts": dict(sorted(state_counts.items())),
        "technical_error_count": len(technical_errors),
        "technical_error_domains": technical_errors,
        "attempts": attempts,
        "resolved_via": resolved_via,
        "resolver_attempts": resolver_attempts,
        "details": details,
    }


def evaluate(
    cases: list[dict[str, str]],
    dns_states: dict[str, DNSState],
    service: EmailValidatorService,
) -> dict:
    observations: list[tuple[str, str]] = []
    categories: list[str] = []
    failures: list[dict] = []
    unscored: list[dict] = []
    evidence_counts: Counter[str] = Counter()

    for case in cases:
        domain = project_domain(case["email"])
        expected, evidence = reference_decision(
            case["email"],
            case["risk_if_deliverable"],
            dns_states.get(domain) if domain else None,
        )
        _, _, actual = service.validate_one(case["email"], persist=False)
        reason_codes = [code.value for code in actual.reason_codes]
        if expected is None or ReasonCode.DNS_LOOKUP_ERROR.value in reason_codes:
            unscored.append(
                {
                    "case_id": case["case_id"],
                    "category": case["category"],
                    "reference_evidence": evidence,
                    "project_reason_codes": reason_codes,
                }
            )
            continue
        observations.append((expected, actual.status.value))
        categories.append(case["category"])
        evidence_counts[evidence] += 1
        if expected != actual.status.value:
            failures.append(
                {
                    "case_id": case["case_id"],
                    "category": case["category"],
                    "email": case["email"],
                    "expected": expected,
                    "actual": actual.status.value,
                    "reference_evidence": evidence,
                    "project_reason_codes": reason_codes,
                }
            )

    if not observations:
        raise RuntimeError("Hiçbir live challenge örneği puanlanamadı.")
    confusion = Counter(observations)
    valid_total = sum(expected == "gecerli" for expected, _ in observations)
    false_nonvalid = sum(
        count
        for (expected, actual), count in confusion.items()
        if expected == "gecerli" and actual != "gecerli"
    )
    raw_accuracy = sum(expected == actual for expected, actual in observations) / len(observations)
    policy_case_count = sum(category == "strict_outer_space" for category in categories)
    aligned_total = len(observations) - policy_case_count
    aligned_correct = sum(
        expected == actual
        for (expected, actual), category in zip(observations, categories, strict=True)
        if category != "strict_outer_space"
    )
    return {
        "measured_at": datetime.now(UTC).isoformat(),
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "evaluation_mode": "independent_strict_syntax_with_shared_live_dns_snapshot",
        "reference": "python-email-validator==2.3.0 strict syntax + shared live DNS snapshot",
        "dataset_size": len(cases),
        "dataset_sha256": FROZEN_DATASET_SHA256,
        "scored_cases": len(observations),
        "unscored_cases": len(unscored),
        "measurement_valid": len(observations) == len(cases),
        "accuracy": round(raw_accuracy, 4),
        "policy_aligned_accuracy": round(aligned_correct / aligned_total, 4),
        "documented_policy_case_count": policy_case_count,
        "false_positive_rate_valid_to_nonvalid": round(false_nonvalid / valid_total, 4)
        if valid_total
        else None,
        **classification_metrics(observations, categories),
        "reference_evidence_counts": dict(sorted(evidence_counts.items())),
        "failures": failures,
        "unscored": unscored,
        "limitations": [
            "No SMTP RCPT TO or mailbox-existence probe is performed.",
            "Only public domain-level DNS is queried; no customer data is used.",
            "The shared DNS snapshot prevents transient resolver bias but does not "
            "independently validate the project's DNS algorithm.",
            "Role, disposable, typo and SMTPUTF8 are risk-policy labels, not proof of non-delivery.",
            "DNS changes over time; the timestamp, resolver and corpus hash must accompany the metric.",
            "This result is not directly comparable with a different project's differently labeled corpus.",
        ],
    }


def markdown(report: dict, resolver_nameservers: list[str]) -> str:
    matrix = report["confusion_matrix"]
    fpr = report["false_positive_rate_valid_to_nonvalid"]
    fpr_text = "ölçülemedi" if fpr is None else f"%{fpr * 100:.2f}"
    snapshot = report["dns_snapshot"]
    class_rows = [
        f"| `{label}` | %{values['precision'] * 100:.2f} | %{values['recall'] * 100:.2f} | "
        f"%{values['f1'] * 100:.2f} | {values['support']} |"
        for label, values in report["per_class"].items()
    ]
    category_rows = [
        f"| `{category}` | {values['correct']}/{values['total']} | %{values['accuracy'] * 100:.2f} |"
        for category, values in report["category_success"].items()
    ]
    return "\n".join(
        [
            "# Görev 1 — 200 Adreslik Canlı DNS Karşılaştırması",
            "",
            "Bu ölçüm, bağımsız strict syntax referansı ve iki tarafa da verilen tek bir",
            "canlı DNS anlık görüntüsüyle proje kararını karşılaştırır. Mailbox varlığını",
            "sınamaz ve müşteri verisi kullanmaz.",
            "",
            f"- Ölçüm zamanı: {report['measured_at']}",
            f"- Ortam: {report['platform']}; Python {report['python_version']}",
            f"- Resolver: {', '.join(resolver_nameservers)}",
            f"- DNS snapshot: {snapshot['domain_count']} tekil domain; "
            f"{snapshot['technical_error_count']} teknik hata",
            f"- DNS durumları: `{json.dumps(snapshot['state_counts'], ensure_ascii=False, sort_keys=True)}`",
            f"- Corpus: {report['dataset_size']} adres; SHA-256 `{report['dataset_sha256']}`",
            f"- Puanlanan: {report['scored_cases']}; teknik nedenle puanlanmayan: "
            f"{report['unscored_cases']}",
            f"- Ölçüm geçerli: {'evet' if report['measurement_valid'] else 'hayır'}",
            f"- Accuracy: %{report['accuracy'] * 100:.2f}",
            f"- Macro precision: %{report['macro_average']['precision'] * 100:.2f}",
            f"- Macro recall: %{report['macro_average']['recall'] * 100:.2f}",
            f"- Macro F1: %{report['macro_average']['f1'] * 100:.2f}",
            f"- Geçerli → geçerli olmayan FPR: {fpr_text}",
            f"- Belgelenmiş trim politikası hariç accuracy: %{report['policy_aligned_accuracy'] * 100:.2f}",
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
            "## Kategori başarısı",
            "",
            "| Kategori | Doğru/Toplam | Başarı |",
            "|---|---:|---:|",
            *category_rows,
            "",
            "## Yanlış sınıflandırmalar",
            "",
            *(
                [
                    f"- `{item['case_id']}` / `{item['category']}`: beklenen `{item['expected']}`, "
                    f"üretilen `{item['actual']}` ({', '.join(item['project_reason_codes'])})"
                    for item in report["failures"]
                ]
                or ["- Yok"]
            ),
            "",
            "## Sınırlar",
            "",
            *[f"- {item}" for item in report["limitations"]],
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acknowledge-live-dns", action="store_true")
    parser.add_argument("--nameserver", action="append")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evaluation/task1-live-challenge-results.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=ROOT / "evaluation/task1-live-challenge-report.md",
    )
    parser.add_argument("--min-accuracy", type=float, default=None)
    parser.add_argument(
        "--dns-timeout",
        type=float,
        default=3.0,
        help="Her DNS denemesi için saniye cinsinden timeout (varsayılan: 3).",
    )
    parser.add_argument(
        "--dns-retries",
        type=int,
        default=2,
        help="Teknik DNS hatasında ek deneme sayısı (varsayılan: 2).",
    )
    args = parser.parse_args()
    if not args.acknowledge_live_dns:
        raise SystemExit("Live DNS is opt-in; pass --acknowledge-live-dns.")

    if args.dns_timeout <= 0:
        raise SystemExit("--dns-timeout sıfırdan büyük olmalıdır.")
    if args.dns_retries < 0:
        raise SystemExit("--dns-retries negatif olamaz.")

    nameservers, nameserver_probes = probe_nameservers(args.nameserver, args.dns_timeout)
    cases = load_cases(args.dataset)
    domains = {domain for case in cases if (domain := project_domain(case["email"]))}

    with TemporaryDirectory(prefix="postnode-live-challenge-") as directory:
        settings = Settings(
            _env_file=None,
            database_url=f"sqlite:///{Path(directory) / 'live-challenge.db'}",
        )
        repository = Repository(settings.database_url, settings.email_hash_secret)
        try:
            resolver_checkers: list[tuple[str, DNSChecker]] = []
            for nameserver in nameservers:
                checker = DNSChecker(repository, args.dns_timeout)
                checker.resolver = dns.resolver.Resolver(configure=False)
                checker.resolver.nameservers = [nameserver]
                checker.resolver.timeout = args.dns_timeout
                checker.resolver.lifetime = args.dns_timeout
                resolver_checkers.append((nameserver, checker))

            dns_states, snapshot_report = resolve_dns_snapshot(
                domains, resolver_checkers, args.dns_retries
            )
            service = EmailValidatorService(
                settings,
                repository,
                StaticDNSChecker(dns_states, default=DNSState.ERROR),
            )
            report = evaluate(cases, dns_states, service)
            report["resolver_nameservers"] = nameservers
            report["nameserver_probes"] = nameserver_probes
            report["dns_timeout_seconds"] = args.dns_timeout
            report["dns_retries"] = args.dns_retries
            report["dns_snapshot"] = snapshot_report
            report["measurement_valid"] = (
                report["scored_cases"] == EXPECTED_SIZE
                and snapshot_report["technical_error_count"] == 0
            )
            report["result_status"] = (
                "valid" if report["measurement_valid"] else "invalid_incomplete_dns"
            )
        finally:
            repository.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(report, nameservers), encoding="utf-8")
    console_report = {
        key: report[key]
        for key in (
            "measured_at",
            "dataset_size",
            "scored_cases",
            "unscored_cases",
            "measurement_valid",
            "result_status",
            "accuracy",
            "policy_aligned_accuracy",
            "false_positive_rate_valid_to_nonvalid",
            "macro_average",
            "confusion_matrix",
            "category_success",
            "reference_evidence_counts",
            "failures",
            "resolver_nameservers",
            "nameserver_probes",
            "dns_snapshot",
        )
    }
    print(json.dumps(console_report, ensure_ascii=False, indent=2))
    if not report["measurement_valid"]:
        raise SystemExit(
            "Canlı DNS ölçümü tamamlanamadı; 200/200 örnek ve sıfır teknik DNS hatası "
            "gereklidir. --dns-timeout/--dns-retries seçenekleriyle yeniden çalıştırın."
        )
    if args.min_accuracy is not None and report["accuracy"] < args.min_accuracy:
        raise SystemExit(
            f"Live challenge accuracy {report['accuracy']:.4f}, alt sınır {args.min_accuracy:.4f}."
        )


if __name__ == "__main__":
    main()
