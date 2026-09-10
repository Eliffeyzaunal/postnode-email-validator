"""Opt-in real DNS latency and cache benchmark for public domains."""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.dns_checker import DNSChecker
from app.repository import Repository


def load_domains(path: Path) -> list[str]:
    values = [
        line.strip().casefold()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(values) != len(set(values)):
        raise ValueError("Live DNS benchmark domains must be unique.")
    return values


def run_benchmark(checker: DNSChecker, domains: list[str]) -> dict:
    started = time.perf_counter()
    cold_results = [checker.lookup(domain) for domain in domains]
    cold_elapsed = time.perf_counter() - started

    started = time.perf_counter()
    warm_results = [checker.lookup(domain) for domain in domains]
    warm_elapsed = time.perf_counter() - started
    if not all(result.from_cache for result in warm_results):
        raise RuntimeError("Second DNS pass was not fully served from the persistent cache.")

    state_counts = dict(sorted(Counter(item.state.value for item in cold_results).items()))
    successful_dns_results = len(domains) - state_counts.get("error", 0)
    return {
        "domain_count": len(domains),
        "cold_elapsed_seconds": round(cold_elapsed, 4),
        "cold_queries_per_second": round(len(domains) / cold_elapsed, 2),
        "warm_elapsed_seconds": round(warm_elapsed, 4),
        "warm_queries_per_second": round(len(domains) / warm_elapsed, 2),
        "cold_state_counts": state_counts,
        "successful_dns_results": successful_dns_results,
        "measurement_valid": successful_dns_results > 0,
        "warm_cache_hits": sum(item.from_cache for item in warm_results),
    }


def markdown(report: dict) -> str:
    states = ", ".join(f"`{key}`={value}" for key, value in report["cold_state_counts"].items())
    validity = (
        "geçerli - en az bir gerçek DNS cevabı alındı"
        if report["measurement_valid"]
        else "GEÇERSİZ - resolver bütün sorguları teknik hata ile döndürdü"
    )
    return "\n".join([
        "# Görev 1 Gerçek DNS Benchmark Sonucu", "",
        f"- Ölçüm zamanı: {report['measured_at']}",
        f"- Ortam: {report['platform']}; Python {report['python_version']}",
        f"- Resolver: {', '.join(report['resolver_nameservers'])}",
        f"- Her turdaki benzersiz, herkese açık alan adı: {report['domain_count']}",
        f"- Ölçüm geçerliliği: {validity}",
        "- Müşteri verisi: kullanılmadı", "",
        "| Ölçüm | Gerçek DNS (soğuk) | Kalıcı cache (sıcak) |",
        "|---|---:|---:|",
        f"| Süre (sn) | {report['cold_elapsed_seconds']:.4f} | {report['warm_elapsed_seconds']:.4f} |",
        f"| Sorgu/sn | {report['cold_queries_per_second']:.2f} | {report['warm_queries_per_second']:.2f} |",
        f"| Cache hit | 0 | {report['warm_cache_hits']} |", "",
        f"DNS durumları: {states}.", "",
        "Bu ölçüm yalnızca gerçek DNS gecikmesini ve cache davranışını gösterir. ",
        "10.000 adreslik deterministik MySQL benchmark'ıyla hız karşılaştırması yapılamaz; ",
        "alan adı sayısı, ağ, resolver ve donanım koşulları farklıdır.", "",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acknowledge-live-dns", action="store_true")
    parser.add_argument(
        "--nameserver",
        action="append",
        help="Optional resolver IP; repeat to configure more than one.",
    )
    parser.add_argument("--domains", type=Path, default=ROOT / "benchmark/live-dns-domains.txt")
    parser.add_argument("--output", type=Path, default=ROOT / "benchmark/live-dns-results.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "benchmark/live-dns-report.md")
    args = parser.parse_args()
    if not args.acknowledge_live_dns:
        raise SystemExit("Live DNS is opt-in; pass --acknowledge-live-dns.")

    with TemporaryDirectory(prefix="postnode-live-dns-") as directory:
        settings = Settings(
            _env_file=None,
            database_url=f"sqlite:///{Path(directory) / 'cache.db'}",
            dns_cache_ttl_seconds=86_400,
        )
        repository = Repository(settings.database_url, settings.email_hash_secret)
        try:
            checker = DNSChecker(repository, settings.dns_timeout_seconds)
            if args.nameserver:
                checker.resolver.nameservers = args.nameserver
            report = {
                "measured_at": datetime.now(UTC).isoformat(),
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "dns_mode": "live_public_domains",
                "customer_data": False,
                "resolver_nameservers": list(checker.resolver.nameservers),
                **run_benchmark(checker, load_domains(args.domains)),
            }
        finally:
            repository.close()

    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["measurement_valid"]:
        raise SystemExit(
            "Resolver gerçek DNS cevabı vermedi; rapor geçersiz olarak kaydedildi. "
            "Ağ erişimi olan hedef ortamda yeniden çalıştırın."
        )


if __name__ == "__main__":
    main()
