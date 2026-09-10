import argparse
import csv
import json
import os
import platform
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import PROJECT_ROOT, Settings
from app.dns_checker import DNSChecker
from app.models import DNSResult, DNSState
from app.repository import Repository
from app.validator import EmailValidatorService


def source_revision() -> dict:
    try:
        sha = os.getenv("GITHUB_SHA") or subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
        dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip())
        return {"commit_sha": sha, "working_tree_dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit_sha": os.getenv("GITHUB_SHA", "unknown"), "working_tree_dirty": None}


class DeterministicCachingDNSChecker(DNSChecker):
    """Ağ yerine sabit cevap üretir; üretimdeki MySQL cache yolunu kullanır."""

    def __init__(self, repository: Repository):
        super().__init__(repository)
        self.network_queries = 0
        self._counter_lock = Lock()
        self.namespace = f"bench-{uuid.uuid4().hex[:12]}"
        self.cache_domains: list[str] = []

    def lookup(self, domain: str) -> DNSResult:
        cache_domain = f"{self.namespace}.{domain}"
        if cache_domain not in self.cache_domains:
            self.cache_domains.append(cache_domain)
        cached_result = super().lookup(cache_domain)
        return DNSResult(domain, cached_result.state, cached_result.detail, cached_result.from_cache)

    def _lookup_uncached(self, domain: str) -> DNSResult:
        with self._counter_lock:
            self.network_queries += 1
        return DNSResult(domain, DNSState.MX, "deterministic benchmark")


def timed_run(
    service: EmailValidatorService, emails: list[str]
) -> tuple[str, float, dict]:
    started = time.perf_counter()
    batch_id, summary, _ = service.validate_many(
        emails, filename="emails-10000.csv", persist=True
    )
    return batch_id, time.perf_counter() - started, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="10.000 adres, kalıcı kayıt ve DNS önbelleği ölçümü")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--require-mysql", action="store_true")
    args = parser.parse_args()
    path = PROJECT_ROOT / "benchmark" / "emails-10000.csv"
    emails = [row["email"] for row in csv.DictReader(path.open(encoding="utf-8"))]
    settings = Settings(domain_concentration_threshold=1.1)
    repository = Repository(settings.database_url, settings.email_hash_secret)
    if args.require_mysql and repository.engine.dialect.name != "mysql":
        repository.close()
        raise SystemExit("Bu teslim ölçümü gerçek MySQL gerektirir; SQLite sonucu kabul edilmez.")
    checker = DeterministicCachingDNSChecker(repository)
    service = EmailValidatorService(settings, repository, checker)
    batch_ids: list[str] = []

    try:
        cold_batch_id, cold_elapsed, cold_summary = timed_run(service, emails)
        batch_ids.append(cold_batch_id)
        cold_queries = checker.network_queries

        checker.network_queries = 0
        warm_batch_id, warm_elapsed, warm_summary = timed_run(service, emails)
        batch_ids.append(warm_batch_id)
        warm_queries = checker.network_queries
        total_stored_rows = repository.count_results_for_batches(batch_ids)

        report = {
            "measured_at": datetime.now(UTC).isoformat(),
            "database_backend": repository.engine.dialect.name,
            "database_server_version": list(repository.engine.dialect.server_version_info or []),
            "python_version": platform.python_version(),
            "platform": platform.system(),
            **source_revision(),
            "dns_mode": "deterministic_stub",
            "customer_data": False,
            "addresses_per_run": len(emails),
            "cold_cache": {
                "elapsed_seconds": round(cold_elapsed, 4),
                "addresses_per_second": round(len(emails) / cold_elapsed, 2),
                "dns_network_queries": cold_queries,
                "summary": cold_summary,
            },
            "warm_cache": {
                "elapsed_seconds": round(warm_elapsed, 4),
                "addresses_per_second": round(len(emails) / warm_elapsed, 2),
                "dns_network_queries": warm_queries,
                "summary": warm_summary,
            },
            "database_rows_written": total_stored_rows,
            "expected_database_rows": len(emails) * 2,
        }
        if cold_queries != 4 or warm_queries != 0 or total_stored_rows != len(emails) * 2:
            raise RuntimeError("Benchmark kabul koşulları sağlanmadı.")
        output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
        if args.markdown:
            args.markdown.parent.mkdir(parents=True, exist_ok=True)
            args.markdown.write_text("\n".join([
                "# Ölçülmüş 10.000 Adres Benchmark Sonucu", "",
                f"- Tarih: {report['measured_at']}",
                f"- Veritabanı: {report['database_backend']} {report['database_server_version']}",
                f"- Python: {report['python_version']}; işletim sistemi: {report['platform']}",
                f"- Commit: {report['commit_sha']}",
                f"- Commit dışı çalışma dosyası değişikliği: {report['working_tree_dirty']}",
                "- Veri sentetiktir; DNS cevapları sabittir; veritabanı işlemleri gerçektir.", "",
                "| Ölçüm | Soğuk önbellek | Sıcak önbellek |",
                "|---|---:|---:|",
                f"| Süre (saniye) | {cold_elapsed:.4f} | {warm_elapsed:.4f} |",
                f"| Adres/saniye | {len(emails) / cold_elapsed:.2f} | {len(emails) / warm_elapsed:.2f} |",
                f"| DNS stub çağrısı | {cold_queries} | {warm_queries} |", "",
                f"Her koşuda {len(emails)} adres işlendi; toplam {total_stored_rows} sonuç satırı yazıldığı doğrulandı.",
                "DNS ağ gecikmesi ölçülmemiştir. Sonuçlar bu donanım ve veritabanı ortamına aittir.", "",
            ]), encoding="utf-8")
        print(output)
    finally:
        repository.delete_batches(batch_ids)
        repository.delete_dns_entries(checker.cache_domains)
        repository.close()


if __name__ == "__main__":
    main()
