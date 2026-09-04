import argparse
from pathlib import Path

from app.blocklist.repository import BlocklistRepository
from app.blocklist.scheduler import BlocklistScheduler
from app.blocklist.service import BlocklistMonitorService
from app.config import Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Postnode blocklist geçmiş raporu")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/blocklist-30-day-report.json"),
    )
    parser.add_argument("--database-url")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings(
        **({"database_url": args.database_url} if args.database_url else {})
    )
    repository = BlocklistRepository(settings.database_url)
    try:
        scheduler = BlocklistScheduler(
            BlocklistMonitorService(settings, repository)
        )
        report = scheduler.history_report(args.days)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        print(report.model_dump_json(indent=2))
        print(f"\nÇıktı: {args.output}")
    finally:
        repository.close()


if __name__ == "__main__":
    main()
