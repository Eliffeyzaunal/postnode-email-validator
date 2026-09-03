import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import PROJECT_ROOT, Settings
from app.dns_checker import StaticDNSChecker
from app.models import DNSState
from app.repository import Repository
from app.validator import EmailValidatorService


def main() -> None:
    path = PROJECT_ROOT / "benchmark" / "emails-10000.csv"
    emails = [row["email"] for row in csv.DictReader(path.open(encoding="utf-8"))]
    checker = StaticDNSChecker({}, default=DNSState.MX)
    settings = Settings(
        database_path=PROJECT_ROOT / "benchmark" / "benchmark.db",
        domain_concentration_threshold=1.1,
    )
    service = EmailValidatorService(settings, Repository(settings.database_path), checker)
    started = time.perf_counter()
    _, summary, _ = service.validate_many(emails, persist=False)
    elapsed = time.perf_counter() - started
    print(json.dumps({
        "addresses": len(emails),
        "elapsed_seconds": round(elapsed, 4),
        "addresses_per_second": round(len(emails) / elapsed, 2),
        "unique_dns_lookups": sum(checker.calls.values()),
        "summary": summary,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
