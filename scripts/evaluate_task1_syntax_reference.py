"""Cross-check Task 1 syntax decisions against an independent reference implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from email_validator import EmailNotValidError, validate_email

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.syntax import validate_syntax


REFERENCE = "python-email-validator==2.3.0"


def build_corpus() -> list[tuple[str, str]]:
    """Build a deterministic corpus without consulting the implementation under test."""
    cases: list[tuple[str, str]] = []

    ascii_locals = [
        "alice", "first.last", "user+tag", "o'brien", "cash$box", "slash/name",
        "equal=name", "under_score", "question?mark", "brace{name}", "pipe|name",
        "a!b", "star*mail", "caret^mail", "back`tick",
    ]
    ascii_domains = [
        "example.com", "mail.example.org", "sample-domain.net", "service.co.uk",
        "xn--bcher-kva.example", "department.example.info", "example.technology",
    ]
    for local in ascii_locals:
        for domain in ascii_domains:
            cases.append(("valid_ascii", f"{local}@{domain}"))

    unicode_locals = [
        "élif", "müller", "δοκιμή", "пользователь", "用户", "उपयोगकर्ता",
        "kullanıcı", "josé", "naïve", "résumé", "françois", "çağrı",
    ]
    idn_domains = [
        "bücher.example", "臺網中心.tw", "郵件.商務", "εχαμπλε.ψομ",
        "пример.рф", "例子.测试", "παράδειγμα.δοκιμή", "مثال.إختبار",
    ]
    for index, local in enumerate(unicode_locals):
        for offset in range(4):
            cases.append(("valid_smtputf8", f"{local}@{idn_domains[(index + offset) % len(idn_domains)]}"))
    for index, domain in enumerate(idn_domains):
        for offset in range(5):
            cases.append(("valid_idn", f"ascii{index}-{offset}@{domain}"))

    malformed_locals = [
        "", ".leading", "trailing.", "two..dots", "white space", 'bad"quote',
        "tab\tinside", "line\ninside", "comma,name", "colon:name", "semi;name",
        "paren(name)", "bracket[name]", "back\\slash", "angle<name>",
    ]
    for index, local in enumerate(malformed_locals):
        for suffix in range(5):
            cases.append(("invalid_local", f"{local}@badlocal{index}-{suffix}.example"))

    malformed_domains = [
        "", "localhost", ".leading.example", "trailing.example.", "two..dots.example",
        "-leading.example", "trailing-.example", "under_score.example", "space name.example",
        "bad!character.example", "[127.0.0.1]", "[IPv6:::1]", "xn--0.example",
    ]
    for index, domain in enumerate(malformed_domains):
        for suffix in range(5):
            local = f"domaincase{index}-{suffix}"
            if domain == "trailing.example.":
                category = "policy_trailing_root_dot"
            elif domain == "xn--0.example":
                category = "invalid_alabel"
            else:
                category = "invalid_domain"
            cases.append((category, f"{local}@{domain}"))

    for index in range(25):
        cases.append(("missing_or_extra_at", f"missing{index}.example.com"))
        cases.append(("missing_or_extra_at", f"double{index}@@example.com"))

    # Policy boundaries are retained rather than silently filtered. Disagreement
    # here is useful evidence of an intentional or accidental scope difference.
    for index in range(20):
        cases.append(("policy_outer_space", f"  spaced{index}@example.com  "))
        cases.append(("policy_single_char_tld", f"single{index}@example.c"))
        cases.append(("policy_quoted_local", f'"quoted {index}"@example.com'))

    length_cases = [
        "x" * 64 + "@example.com",
        "x" * 65 + "@example.com",
        "é" * 32 + "@example.com",
        "é" * 33 + "@example.com",
        "a@" + "x" * 63 + ".example",
        "a@" + "x" * 64 + ".example",
    ]
    for index in range(5):
        for value in length_cases:
            local, domain = value.rsplit("@", 1)
            category = (
                "policy_smtputf8_octet_limit"
                if not local.isascii() and len(local.encode("utf-8")) > 64
                else "length_boundary"
            )
            cases.append((category, f"{local}@{index}.{domain}" if index else value))

    # Preserve first occurrence so the corpus hash and sample count are stable.
    unique: dict[str, str] = {}
    for category, email in cases:
        unique.setdefault(email, category)
    return [(category, email) for email, category in unique.items()]


def reference_accepts(email: str) -> bool:
    try:
        validate_email(
            email,
            allow_smtputf8=True,
            allow_quoted_local=False,
            allow_domain_literal=False,
            allow_display_name=False,
            check_deliverability=False,
            globally_deliverable=False,
            strict=True,
        )
        return True
    except EmailNotValidError:
        return False


def evaluate() -> dict:
    corpus = build_corpus()
    counts: Counter[tuple[bool, bool]] = Counter()
    aligned_counts: Counter[tuple[bool, bool]] = Counter()
    category_counts: Counter[str] = Counter()
    category_matches: Counter[str] = Counter()
    mismatches = []
    for category, email in corpus:
        expected = reference_accepts(email)
        actual = validate_syntax(email, allow_smtputf8=True).valid
        counts[(expected, actual)] += 1
        if not category.startswith("policy_"):
            aligned_counts[(expected, actual)] += 1
        category_counts[category] += 1
        if expected == actual:
            category_matches[category] += 1
        elif len(mismatches) < 50:
            mismatches.append(
                {
                    "category": category,
                    "email": email,
                    "reference_valid": expected,
                    "project_valid": actual,
                }
            )

    tp = counts[(True, True)]
    fp = counts[(False, True)]
    fn = counts[(True, False)]
    tn = counts[(False, False)]
    total = len(corpus)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    corpus_hash = hashlib.sha256(
        "\n".join(f"{category}\t{email}" for category, email in corpus).encode("utf-8")
    ).hexdigest()
    aligned_total = sum(aligned_counts.values())
    aligned_matches = aligned_counts[(True, True)] + aligned_counts[(False, False)]
    return {
        "metric_name": "syntax_reference_agreement",
        "reference": REFERENCE,
        "corpus_size": total,
        "corpus_sha256": corpus_hash,
        "agreement": round((tp + tn) / total, 4),
        "policy_aligned_corpus_size": aligned_total,
        "policy_aligned_agreement": round(aligned_matches / aligned_total, 4),
        "valid_precision": round(precision, 4),
        "valid_recall": round(recall, 4),
        "valid_f1": round(f1, 4),
        "confusion": {
            "reference_valid_project_valid": tp,
            "reference_invalid_project_valid": fp,
            "reference_valid_project_invalid": fn,
            "reference_invalid_project_invalid": tn,
        },
        "category_agreement": {
            category: {
                "matched": category_matches[category],
                "total": count,
                "agreement": round(category_matches[category] / count, 4),
            }
            for category, count in sorted(category_counts.items())
        },
        "mismatch_count": fp + fn,
        "mismatch_examples": mismatches,
        "documented_policy_differences": {
            "policy_outer_space": "The service trims surrounding input whitespace before validation.",
            "policy_single_char_tld": "The service requires a final domain label of at least two characters.",
            "policy_trailing_root_dot": "The service normalizes a trailing DNS root dot.",
            "policy_smtputf8_octet_limit": "The service applies RFC 5321's 64-octet local-part limit to UTF-8.",
        },
        "baseline_observation": {
            "initial_agreement": 0.8732,
            "finding": "Malformed pre-encoded Punycode A-labels were accepted by the stdlib IDNA codec.",
            "resolution": "IDNA 2008/UTS 46 validation was made explicit with the idna package.",
        },
        "scope": (
            "Syntax-only agreement with an independent implementation; no DNS, disposable, "
            "role-account, typo, SMTP delivery, or real-customer accuracy claim."
        ),
    }


def write_markdown(report: dict, path: Path) -> None:
    confusion = report["confusion"]
    rows = [
        f"| `{category}` | {values['matched']}/{values['total']} | %{values['agreement'] * 100:.2f} |"
        for category, values in report["category_agreement"].items()
    ]
    mismatch_rows = [
        f"| `{item['category']}` | `{item['email']}` | {item['reference_valid']} | {item['project_valid']} |"
        for item in report["mismatch_examples"][:20]
    ]
    lines = [
        "# Görev 1 Bağımsız Syntax Referans Karşılaştırması",
        "",
        f"Referans: `{report['reference']}` (Unlicense). Bu ölçüm yalnız syntax karar uyumudur;",
        "genel adres doğruluğu veya teslim edilebilirlik oranı değildir.",
        "",
        f"- Corpus: {report['corpus_size']} görülmemiş/deterministik örnek",
        f"- Syntax agreement: %{report['agreement'] * 100:.2f}",
        f"- Belgelenmiş politika farkları hariç uyum: %{report['policy_aligned_agreement'] * 100:.2f} "
        f"({report['policy_aligned_corpus_size']} örnek)",
        f"- Geçerli precision: %{report['valid_precision'] * 100:.2f}",
        f"- Geçerli recall: %{report['valid_recall'] * 100:.2f}",
        f"- Geçerli F1: %{report['valid_f1'] * 100:.2f}",
        f"- Politika/uygulama farkı: {report['mismatch_count']}",
        f"- Corpus SHA-256: `{report['corpus_sha256']}`",
        "",
        "## İkili confusion matrix",
        "",
        "| Referans \\ Proje | Geçerli | Geçersiz |",
        "|---|---:|---:|",
        f"| Geçerli | {confusion['reference_valid_project_valid']} | {confusion['reference_valid_project_invalid']} |",
        f"| Geçersiz | {confusion['reference_invalid_project_valid']} | {confusion['reference_invalid_project_invalid']} |",
        "",
        "## Kategori uyumu",
        "",
        "| Kategori | Uyum/Toplam | Oran |",
        "|---|---:|---:|",
        *rows,
        "",
        "## İlk fark örnekleri",
        "",
        "| Kategori | Adres | Referans | Proje |",
        "|---|---|---:|---:|",
        *mismatch_rows,
        "",
        "Ham sonuçtan hiçbir fark silinmez. Politika uyumlu ikinci oran yalnız `policy_*` olarak",
        "önceden tanımlanmış dış boşluk, DNS kök noktası ve tek karakterli TLD farklarını dışarıda tutar.",
        "İlk çalıştırma ayrıca geçersiz bir Punycode A-label kabulünü ortaya çıkarmış; bu hata",
        "`idna` ile açık IDNA 2008/UTS 46 doğrulaması eklenerek düzeltilmiştir.",
        "Bu corpus mevcut kuralları değiştirmek için kullanılmaz; sonuç bir sonraki sürümle yeniden ölçülür.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--min-agreement", type=float, default=None)
    args = parser.parse_args()
    report = evaluate()
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    if args.markdown:
        write_markdown(report, args.markdown)
    print(output)
    if args.min_agreement is not None and report["agreement"] < args.min_agreement:
        raise SystemExit(
            f"Syntax agreement {report['agreement']:.4f}, alt sınır {args.min_agreement:.4f}."
        )


if __name__ == "__main__":
    main()
