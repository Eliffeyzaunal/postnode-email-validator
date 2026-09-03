import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def write_evaluation() -> None:
    rows: list[tuple[str, str, str]] = []
    rows += [(f"valid.user{i:03d}.checked@gmail.com", "gecerli", "mx") for i in range(1, 81)]
    rows += [(f"role{i:03d}@mailinator.com", "supheli", "mx") for i in range(1, 21)]
    rows += [(f"user{i:03d}@gmial.com", "supheli", "mx") for i in range(1, 21)]
    rows += [(f"broken{i:03d}.example.com", "gecersiz", "none") for i in range(1, 21)]
    rows += [(f"bad..local{i:03d}@example.com", "gecersiz", "mx") for i in range(1, 21)]
    rows += [(f"user{i:03d}@missing.example", "gecersiz", "nxdomain") for i in range(1, 21)]
    rows += [(f"user{i:03d}@error.example", "supheli", "error") for i in range(1, 21)]
    path = ROOT / "evaluation" / "evaluation.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["email", "expected_status", "dns_state"])
        writer.writerows(rows)


def write_benchmark() -> None:
    path = ROOT / "benchmark" / "emails-10000.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["email"])
        domains = ["gmail.com", "outlook.com", "yandex.com", "example.com"]
        for i in range(10_000):
            writer.writerow([f"benchmark.user{i:05d}@{domains[i % len(domains)]}"])


if __name__ == "__main__":
    write_evaluation()
    write_benchmark()
