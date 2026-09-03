import csv
import json
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import PROJECT_ROOT, Settings
from app.dns_checker import DNSChecker
from app.models import DNSResult, DNSState
from app.repository import Repository
from app.validator import EmailValidatorService


class DeterministicCachingDNSChecker(DNSChecker):
    """Ağ yerine sabit cevap üretir; gerçek SQLite cache yolunu kullanır."""

    def __init__(self, repository: Repository):
        super().__init__(repository)
        self.network_queries = 0
        self._counter_lock = Lock()

    def _lookup_uncached(self, domain: str) -> DNSResult:
        with self._counter_lock:
            self.network_queries += 1
        return DNSResult(domain, DNSState.MX, "deterministic benchmark")


def timed_run(service: EmailValidatorService, emails: list[str]) -> tuple[float, dict]:
    started = time.perf_counter()
    _, summary, _ = service.validate_many(emails, filename="emails-10000.csv", persist=True)
    return time.perf_counter() - started, summary


def main() -> None:
    path = PROJECT_ROOT / "benchmark" / "emails-10000.csv"
    emails = [row["email"] for row in csv.DictReader(path.open(encoding="utf-8"))]

    with TemporaryDirectory(prefix="postnode-benchmark-") as directory:
        settings = Settings(
            database_path=Path(directory) / "benchmark.db",
            domain_concentration_threshold=1.1,
        )
        repository = Repository(settings.database_path)
        checker = DeterministicCachingDNSChecker(repository)
        service = EmailValidatorService(settings, repository, checker)

        cold_elapsed, cold_summary = timed_run(service, emails)
        cold_queries = checker.network_queries

        checker.network_queries = 0
        warm_elapsed, warm_summary = timed_run(service, emails)
        warm_queries = checker.network_queries

        # İki tam koşunun sonuçlarının gerçekten SQLite'a yazıldığını doğrula.
        with repository.session() as connection:
            total_stored_rows = connection.execute(
                "SELECT COUNT(*) FROM validation_results"
            ).fetchone()[0]

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
        "sqlite_rows_written": total_stored_rows,
        "expected_sqlite_rows": len(emails) * 2,
    }
    if cold_queries != 4 or warm_queries != 0 or total_stored_rows != len(emails) * 2:
        raise RuntimeError("Benchmark kabul koşulları sağlanmadı.")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
