import argparse
import json
import signal
from pathlib import Path
from threading import Event

from app.blocklist.repository import BlocklistRepository
from app.blocklist.scheduler import BlocklistScheduler
from app.blocklist.service import BlocklistMonitorService
from app.config import Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Postnode periyodik blocklist izleyicisi")
    parser.add_argument("--interval", type=int, help="Kontrol aralığı (saniye)")
    parser.add_argument("--once", action="store_true", help="Bir tur çalışıp çık")
    parser.add_argument("--database-url")
    parser.add_argument("--dns-mode", choices=["fake", "live"])
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/blocklist-last-run.json"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    overrides = {}
    if args.database_url:
        overrides["database_url"] = args.database_url
    if args.dns_mode:
        overrides["blocklist_dns_mode"] = args.dns_mode
    if args.interval:
        overrides["blocklist_interval_seconds"] = args.interval
    settings = Settings(**overrides)
    repository = BlocklistRepository(settings.database_url)
    service = BlocklistMonitorService(settings, repository)
    scheduler = BlocklistScheduler(service)
    stop_event = Event()

    def stop(_signum, _frame):
        stop_event.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        if args.once:
            result = scheduler.run_cycle()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            print(result.model_dump_json(indent=2))
            print(f"\nÇıktı: {args.output}")
        else:
            print(
                json.dumps(
                    {
                        "status": "started",
                        "interval_seconds": scheduler.interval_seconds,
                        "dns_mode": settings.blocklist_dns_mode,
                    },
                    ensure_ascii=False,
                )
            )
            scheduler.run_forever(stop_event)
    finally:
        repository.close()


if __name__ == "__main__":
    main()
