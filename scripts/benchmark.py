import csv
import json
import sys
import time
import uuid
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import PROJECT_ROOT, Settings
from app.dns_checker import DNSChecker
from app.models import DNSResult, DNSState
from app.repository import Repository
from app.validator import EmailValidatorService


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
    path = PROJECT_ROOT / "benchmark" / "emails-10000.csv"
    emails = [row["email"] for row in csv.DictReader(path.open(encoding="utf-8"))]
    settings = Settings(domain_concentration_threshold=1.1)
    repository = Repository(settings.database_url)
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
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        repository.delete_batches(batch_ids)
        repository.delete_dns_entries(checker.cache_domains)
        repository.close()


if __name__ == "__main__":
    main()
