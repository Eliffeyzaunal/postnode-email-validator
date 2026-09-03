import csv
import json
import sys
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import PROJECT_ROOT, Settings
from app.dns_checker import StaticDNSChecker
from app.models import DNSState, Status
from app.repository import Repository
from app.validator import EmailValidatorService


STATE_MAP = {
    "mx": DNSState.MX,
    "nxdomain": DNSState.NXDOMAIN,
    "error": DNSState.ERROR,
    "no_mail_host": DNSState.NO_MAIL_HOST,
}


def main() -> None:
    dataset = PROJECT_ROOT / "evaluation" / "evaluation.csv"
    rows = list(csv.DictReader(dataset.open(encoding="utf-8")))
    states = {
        row["email"].rsplit("@", 1)[1].casefold(): STATE_MAP[row["dns_state"]]
        for row in rows if "@" in row["email"] and row["dns_state"] in STATE_MAP
    }
    with TemporaryDirectory(prefix="postnode-evaluation-") as directory:
        database_url = f"sqlite:///{(Path(directory) / 'evaluation.db').as_posix()}"
        settings = Settings(
            database_url=database_url,
            domain_concentration_min_list_size=100_000,
        )
        repository = Repository(database_url)
        try:
            service = EmailValidatorService(settings, repository, StaticDNSChecker(states))
            _, _, results = service.validate_many([row["email"] for row in rows], persist=False)
        finally:
            repository.close()
    expected = [Status(row["expected_status"]) for row in rows]
    correct = sum(actual.status == wanted for actual, wanted in zip(results, expected, strict=True))
    valid_total = sum(wanted == Status.VALID for wanted in expected)
    false_invalid = sum(
        actual.status == Status.INVALID and wanted == Status.VALID
        for actual, wanted in zip(results, expected, strict=True)
    )
    confusion = Counter((wanted.value, actual.status.value) for actual, wanted in zip(results, expected, strict=True))
    report = {
        "dataset_size": len(rows),
        "accuracy": round(correct / len(rows), 4),
        "false_positive_rate_valid_to_invalid": round(false_invalid / valid_total, 4) if valid_total else 0,
        "confusion": {f"{wanted}->{actual}": count for (wanted, actual), count in sorted(confusion.items())},
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
