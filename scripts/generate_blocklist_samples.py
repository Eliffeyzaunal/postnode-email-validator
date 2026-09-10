"""Generate simulated 30-day delivery examples using the real repository logic.

Only a temporary SQLite database, fake DNS and an accelerated fixed clock are
used. This is not a record of operating a live monitor for thirty days.
"""
import argparse
import itertools
import json
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.blocklist.config_loader import load_assets
from app.blocklist.models import BlocklistHistoryReport, BlocklistNotification, DNSResponse, DNSResponseState
from app.blocklist.service import BlocklistMonitorService
from app.config import Settings


def generate(output_dir: Path) -> dict:
    end = datetime(2026, 9, 8, 9, tzinfo=UTC)
    start = end - timedelta(days=30)
    examples = {}
    with TemporaryDirectory(prefix="postnode-blocklist-simulation-") as directory:
        service = BlocklistMonitorService(Settings(
            _env_file=None, database_url=f"sqlite:///{Path(directory) / 'simulation.db'}",
            blocklist_dns_mode="fake",
        ))
        repository = service.repository
        assets = load_assets(service.settings.blocklist_assets_path)
        counter = itertools.count()
        try:
            with patch("app.blocklist.repository.datetime") as clock, patch(
                "app.blocklist.repository.uuid.uuid4",
                side_effect=lambda: uuid.uuid5(uuid.NAMESPACE_URL, f"postnode-sample-event-{next(counter)}"),
            ):
                for hour in range(720):
                    tick = start + timedelta(hours=hour + 1)
                    clock.now.return_value = tick
                    if hour in (30, 31, 719):
                        answer = DNSResponse(state=DNSResponseState.TIMEOUT, detail="Simulated DNS timeout")
                    elif 10 <= hour < 20 or 32 <= hour < 40:
                        answer = DNSResponse(state=DNSResponseState.NXDOMAIN)
                    else:
                        answer = DNSResponse(state=DNSResponseState.OK, a_records=["127.0.0.2"],
                                             txt_records=["SpamCop resmi DNSBL test girdisi"])
                    service.dns_client.set_response("2.0.0.127.bl.spamcop.net", answer)
                    results = [service.checker.check(asset, provider).model_copy(update={"checked_at": tick})
                               for asset in assets for provider in service.providers
                               if asset.type in provider.asset_types]
                    run_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"postnode-sample-run-{hour}"))
                    repository.mark_monitor_started("default", 3600, tick)
                    notifications = repository.save_run(run_id, "simulated-official-test-assets.json", results)
                    repository.mark_monitor_completed("default", 3600, run_id, tick)
                    for notification in notifications:
                        if notification.provider_id == "spamcop" and notification.type.value in {"listed", "delisted"}:
                            examples.setdefault(notification.type.value, notification.model_dump(mode="json"))
            history = repository.history_report(30, "default", 3600, 300, end)
            report = history.model_dump(mode="json")
            BlocklistHistoryReport.model_validate(report)
            assert report["total_runs"] == 720 and report["total_checks"] == 7200
            assert len(report["unresolved_listings"]) == 1
            for notification in examples.values():
                BlocklistNotification.model_validate(notification)
        finally:
            repository.close()
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {"blocklist-30-day-report.json": report,
             "blocklist-notification-listed.json": examples["listed"],
             "blocklist-notification-delisted.json": examples["delisted"]}
    for filename, content in files.items():
        (output_dir / filename).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "simulation": True, "dns_mode": "fake", "database_backend": "temporary SQLite",
        "clock": "accelerated, fixed; not real monitoring history", "hours_simulated": 720,
        "real_customer_data": False, "generated_by": "scripts/generate_blocklist_samples.py",
        "files": list(files),
    }
    (output_dir / "generation-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "samples")
    print(json.dumps(generate(parser.parse_args().output_dir), indent=2))
