import os
import uuid

import pytest

from app.config import PROJECT_ROOT, Settings
from app.blocklist.models import BlocklistCheckRequest, MonitoredAsset
from app.blocklist.repository import BlocklistRepository
from app.blocklist.scheduler import BlocklistScheduler
from app.blocklist.service import BlocklistMonitorService
from app.dns_checker import StaticDNSChecker
from app.models import DNSState
from app.repository import Repository
from app.validator import EmailValidatorService


MYSQL_URL = os.getenv("TEST_MYSQL_DATABASE_URL")


@pytest.mark.skipif(not MYSQL_URL, reason="MySQL entegrasyon adresi tanımlı değil.")
def test_mysql_repository_round_trip():
    settings = Settings(
        database_url=MYSQL_URL,
        disposable_domains_path=PROJECT_ROOT / "data" / "disposable_domains.txt",
        role_accounts_path=PROJECT_ROOT / "data" / "role_accounts.txt",
        domain_typos_path=PROJECT_ROOT / "data" / "domain_typos.json",
    )
    repository = Repository(settings.database_url)
    service = EmailValidatorService(
        settings,
        repository,
        StaticDNSChecker({"gmail.com": DNSState.MX}),
    )
    batch_id = ""
    try:
        raw_email = f"integration-{uuid.uuid4().hex[:10]}@gmail.com"
        batch_id, summary, _ = service.validate_many(
            [raw_email],
            filename="mysql-integration.csv",
        )
        metadata = repository.get_batch(batch_id)
        stored = repository.get_results(batch_id)

        assert summary["total"] == 1
        assert metadata is not None
        assert metadata["filename"] == "mysql-integration.csv"
        assert len(stored) == 1
        assert stored[0]["status"] == "gecerli"
        assert stored[0]["masked_email"].endswith("@gmail.com")
        assert raw_email not in repr(stored)
    finally:
        repository.delete_batches([batch_id] if batch_id else [])
        repository.close()


@pytest.mark.skipif(not MYSQL_URL, reason="MySQL entegrasyon adresi tanımlı değil.")
def test_mysql_blocklist_repository_round_trip(tmp_path):
    asset_id = f"mysql-blocklist-{uuid.uuid4().hex}"
    monitor_name = f"mysql-monitor-{uuid.uuid4().hex}"
    assets_path = tmp_path / "mysql-assets.json"
    assets_path.write_text(
        '{"assets":[{"id":"%s","type":"ip","value":"127.0.0.2"}]}'
        % asset_id,
        encoding="utf-8",
    )
    settings = Settings(
        database_url=MYSQL_URL,
        blocklist_providers_path=PROJECT_ROOT / "config" / "blocklists.json",
        blocklist_assets_path=assets_path,
        blocklist_fake_dns_path=PROJECT_ROOT / "data" / "blocklist_fake_dns.json",
    )
    repository = BlocklistRepository(settings.database_url)
    service = BlocklistMonitorService(settings, repository)
    run_id = ""
    try:
        request = BlocklistCheckRequest(
            assets=[MonitoredAsset(id=asset_id, type="ip", value="127.0.0.2")]
        )
        report = service.run_once(request)
        run_id = report.run_id
        stored = repository.get_run(run_id)

        assert stored is not None
        assert stored["total_checks"] == 4
        assert len(stored["results"]) == 4
        assert {item["status"] for item in stored["results"]} == {
            "listed",
            "unavailable",
        }

        scheduler = BlocklistScheduler(service, monitor_name=monitor_name)
        scheduled_report = scheduler.run_cycle()
        health = scheduler.status()
        history = scheduler.history_report(30)

        assert health.status == "healthy"
        assert history.total_runs >= 2
        assert history.total_checks >= 8
        repository.delete_run(scheduled_report.run_id)
    finally:
        if run_id:
            repository.delete_run(run_id)
        repository.delete_states([asset_id])
        repository.delete_monitor(monitor_name)
        repository.close()
