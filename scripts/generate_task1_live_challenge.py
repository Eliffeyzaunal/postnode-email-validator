"""Generate the frozen 200-address public-DNS Task 1 challenge corpus."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "evaluation/task1-live-challenge.csv"


def build_cases() -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []

    def add(email: str, category: str, risk: str, rationale: str) -> None:
        cases.append(
            {
                "case_id": f"live-{len(cases) + 1:03d}",
                "email": email,
                "category": category,
                "risk_if_deliverable": risk,
                "rationale": rationale,
            }
        )

    public_domains = [
        "gmail.com", "outlook.com", "yahoo.com", "proton.me", "protonmail.com",
        "fastmail.com", "icloud.com", "zoho.com", "gmx.com", "mail.com",
        "yandex.com", "aol.com", "hotmail.com", "tutanota.com", "t-online.de",
    ]
    neutral_locals = ["task1.audit", "quality.check", "sample+tag", "mail.validation"]
    for domain in public_domains:
        for local in neutral_locals:
            add(
                f"{local}@{domain}",
                "neutral_public_domain",
                "none",
                "Tarafsız yerel bölüm; bağımsız referans syntax ve canlı DNS sonucunu belirler.",
            )

    role_locals = [
        "info", "support", "sales-eu", "hr", "security", "postmaster",
        "hostmaster", "billing", "careers", "iletisim",
    ]
    role_domains = ["gmail.com", "outlook.com", "proton.me", "fastmail.com"]
    for local in role_locals:
        for domain in role_domains:
            add(
                f"{local}@{domain}",
                "role_account",
                "role_account",
                "Canlı DNS kabul ederse ortak/rol hesabı olarak şüpheli beklenir.",
            )

    disposable_domains = [
        "mailinator.com", "guerrillamail.com", "guerrillamailblock.com",
        "sharklasers.com", "yopmail.com", "yopmail.fr", "10minutemail.com",
        "temp-mail.org", "yopmail.fr", "moakt.com",
    ]
    seen_disposable_domains: set[str] = set()
    for domain in disposable_domains:
        repeated_domain = domain in seen_disposable_domains
        seen_disposable_domains.add(domain)
        suffixes = ("gamma", "delta") if repeated_domain else ("alpha", "beta")
        for suffix in suffixes:
            add(
                f"challenge.{suffix}@{domain}",
                "disposable_domain",
                "disposable_domain",
                "Canlı DNS kabul ederse bağımsız disposable kategorisi nedeniyle şüpheli beklenir.",
            )

    typo_domains = [
        "gamil.com", "gmai.com", "gmail.co", "gmail.con", "gmail.om",
        "gmailc.om", "gmal.com", "gmial.com", "gmaill.com", "hitmail.com",
        "hotmai.com", "hotmail.co", "hotmail.con", "hotmial.com", "iclod.com",
        "outlok.com", "outllok.com", "outlook.co", "yahho.com", "yaho.com",
    ]
    for index, domain in enumerate(typo_domains, 1):
        add(
            f"typo.audit{index}@{domain}",
            "provider_typo",
            "provider_typo",
            "Canlı DNS kabul ederse gözden geçirilmiş sağlayıcı typo'su nedeniyle şüpheli beklenir.",
        )

    invalid_syntax = [
        "missing-at.example.com",
        "double@@gmail.com",
        "@gmail.com",
        ".leading@gmail.com",
        "trailing.@gmail.com",
        "two..dots@gmail.com",
        "white space@gmail.com",
        "comma,name@gmail.com",
        "colon:name@gmail.com",
        "semi;name@gmail.com",
        "paren(name)@gmail.com",
        "bracket[name]@gmail.com",
        "back\\slash@gmail.com",
        "angle<name>@gmail.com",
        "tab\tinside@gmail.com",
        'quote"inside@gmail.com',
        "local@localhost",
        "local@-leading.com",
        "local@trailing-.com",
        "local@under_score.com",
        "local@two..dots.com",
        "local@space name.com",
        "local@bad!character.com",
        "local@xn--0.example",
        f"{'x' * 65}@gmail.com",
    ]
    for email in invalid_syntax:
        add(
            email,
            "invalid_syntax",
            "none",
            "Bağımsız strict syntax referansının reddetmesi beklenen örnek.",
        )

    nonexistent_domains = [
        "postnode-eval-a01.gmail.com", "postnode-eval-a02.outlook.com",
        "postnode-eval-a03.yahoo.com", "postnode-eval-a04.proton.me",
        "postnode-eval-a05.fastmail.com", "postnode-eval-a06.icloud.com",
        "postnode-eval-a07.zoho.com", "postnode-eval-a08.gmx.com",
        "postnode-eval-a09.mail.com", "postnode-eval-a10.yandex.com",
        "postnode-eval-a11.aol.com", "postnode-eval-a12.hotmail.com",
        "postnode-eval-a13.tutanota.com", "postnode-eval-a14.t-online.de",
        "postnode-eval-a15.protonmail.com",
    ]
    for index, domain in enumerate(nonexistent_domains, 1):
        add(
            f"dns.audit{index}@{domain}",
            "nonexistent_subdomain",
            "none",
            "Syntax geçerli; bağımsız canlı DNS referansının reddetmesi beklenir.",
        )

    unicode_locals = [
        "élif", "müller", "çağrı", "josé", "naïve",
        "δοκιμή", "пользователь", "用户", "résumé", "françois",
    ]
    unicode_domains = ["gmail.com", "outlook.com", "proton.me", "fastmail.com", "icloud.com"]
    for index, local in enumerate(unicode_locals):
        add(
            f"{local}@{unicode_domains[index % len(unicode_domains)]}",
            "smtputf8",
            "smtputf8",
            "Canlı DNS kabul ederse SMTPUTF8 gereksinimi nedeniyle şüpheli beklenir.",
        )

    for index, domain in enumerate(public_domains[:10], 1):
        add(
            f"  outer.space{index}@{domain}  ",
            "strict_outer_space",
            "none",
            "Strict harici referans boşluklu girdiyi reddeder; servis bilinçli olarak trim eder.",
        )

    if len(cases) != 200:
        raise RuntimeError(f"Corpus must contain exactly 200 rows, got {len(cases)}.")
    if len({case["email"] for case in cases}) != len(cases):
        raise RuntimeError("Corpus email values must be unique.")
    return cases


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("case_id", "email", "category", "risk_if_deliverable", "rationale"),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(build_cases())
    print(OUTPUT)


if __name__ == "__main__":
    main()
