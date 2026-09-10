import asyncio
from datetime import UTC, datetime, timedelta
from threading import Event

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert, select

import app.main as main_module
from app.blocklist.models import DNSResponse, DNSResponseState
from app.blocklist.repository import (
    BlocklistRepository,
    blocklist_runs,
    blocklist_states,
    metadata,
)
from app.blocklist.scheduler import BlocklistScheduler
from app.blocklist.service import BlocklistMonitorService
from app.config import Settings


def test_upload_does_not_block_other_requests(service, blocklist_service, monkeypatch):
    entered, release = Event(), Event()
    original_validate = service.validate_many

    def slow_validate(*args, **kwargs):
        entered.set()
        # Bound the regression failure: the old async handler blocks for 5s.
        release.wait(5)
        return original_validate(*args, **kwargs)

    monkeypatch.setattr(service, "validate_many", slow_validate)
    monkeypatch.setattr(main_module, "get_service", lambda: service)
    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(_env_file=None))
    monkeypatch.setattr(
        main_module, "get_blocklist_scheduler", lambda: BlocklistScheduler(blocklist_service)
    )

    async def exercise():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main_module.app), base_url="http://test"
        ) as client:
            upload = asyncio.create_task(client.post(
                "/api/v1/validate/file",
                files={"file": ("emails.csv", b"email\na@gmail.com\n", "text/csv")},
            ))
            try:
                assert await asyncio.to_thread(entered.wait, 2)
                health = await asyncio.wait_for(client.get("/health"), timeout=2)
                assert health.status_code == 200
                assert not upload.done(), "Upload blocked the event loop until validation ended"
            finally:
                release.set()
                response = await upload
            assert response.status_code == 200
            assert response.json()["summary"]["total"] == 1
            assert "a@gmail.com" not in response.text

    asyncio.run(exercise())


@pytest.mark.parametrize("required", [False, True])
@pytest.mark.parametrize("state", ["not_started", "stopped", "running", "healthy", "error", "missed"])
def test_health_monitor_requirement(service, blocklist_service, monkeypatch, required, state):
    repository = blocklist_service.repository
    now = datetime.now(UTC)
    if state == "stopped":
        repository.mark_monitor_stopped("default", 3600, now)
    elif state in {"running", "missed"}:
        repository.mark_monitor_started(
            "default", 3600, now - timedelta(seconds=4000) if state == "missed" else now
        )
    elif state == "healthy":
        BlocklistScheduler(blocklist_service).run_cycle()
    elif state == "error":
        repository.mark_monitor_failed("default", 3600, "test failure", now)
    monkeypatch.setattr(main_module, "get_service", lambda: service)
    monkeypatch.setattr(
        main_module, "get_settings",
        lambda: Settings(_env_file=None, blocklist_monitor_required=required),
    )
    monkeypatch.setattr(
        main_module, "get_blocklist_scheduler", lambda: BlocklistScheduler(blocklist_service)
    )
    response = TestClient(main_module.app).get("/health")
    degraded = state in {"error", "missed"} or (required and state in {"not_started", "stopped"})
    assert response.status_code == (503 if degraded else 200)
    assert response.json()["status"] == ("degraded" if degraded else "ok")
    assert response.json()["blocklist_monitor"] == state
    assert response.json()["blocklist_monitor_required"] is required


def test_fake_and_live_have_independent_history_alarms_and_heartbeats(blocklist_service):
    fake = blocklist_service
    fake_scheduler = BlocklistScheduler(fake)
    first = fake_scheduler.run_cycle()
    live_settings = fake.settings.model_copy(update={"blocklist_dns_mode": "live"})
    live_repository = BlocklistRepository(live_settings.database_url, dns_mode="live")
    try:
        # Inject deterministic answers; this test never contacts public DNS.
        live = BlocklistMonitorService(live_settings, live_repository, dns_client=fake.dns_client)
        live_scheduler = BlocklistScheduler(live)
        assert live_scheduler.status().status == "not_started"
        live_report = live_scheduler.run_cycle()
        assert len(live_report.notifications) == 5
        assert all(item.dns_mode == "live" for item in live_report.notifications)
        assert fake.run_once().notifications == []
        assert fake_scheduler.history_report().total_runs == 2
        assert live_scheduler.history_report().total_runs == 1
        assert live_scheduler.history_report().listed_events == 5
        live_repository.mark_monitor_stopped("default", 3600)
        assert fake_scheduler.status().status == "healthy"
        assert live_scheduler.status().status == "stopped"

        # Retention and cleanup must not cross the DNS mode boundary.
        live_repository.delete_history_before(datetime.now(UTC) + timedelta(days=1), "default")
        assert live_repository.get_run(live_report.run_id) is None
        assert fake.repository.get_run(first.run_id)["dns_mode"] == "fake"
        live_repository.delete_states([item.asset_id for item in first.results])
        assert len(fake_scheduler.history_report().current_listings) == 5
    finally:
        live_repository.close()


def test_mode_is_persisted_across_repository_restarts(blocklist_service):
    report = blocklist_service.run_once()
    reopened = BlocklistRepository(blocklist_service.settings.database_url, dns_mode="live")
    try:
        assert reopened.get_run(report.run_id)["dns_mode"] == "fake"
        assert {item["dns_mode"] for item in reopened.get_notifications(report.run_id)} == {"fake"}
        assert reopened.history_report(30, "default", 3600, 300).total_runs == 0
    finally:
        reopened.close()


def test_service_rejects_mismatched_repository_mode(blocklist_service):
    settings = blocklist_service.settings.model_copy(update={"blocklist_dns_mode": "live"})
    with pytest.raises(ValueError, match="DNS modu aynı"):
        BlocklistMonitorService(settings, blocklist_service.repository)


@pytest.mark.parametrize("recovery", [DNSResponseState.OK, DNSResponseState.NXDOMAIN])
@pytest.mark.parametrize("failure", ["query_error", "unavailable"])
def test_unconfirmed_listings_remain_visible_until_definitive_result(blocklist_service, recovery, failure):
    service = blocklist_service
    scheduler = BlocklistScheduler(service)
    initial = service.run_once()
    original = next(item for item in initial.notifications if item.provider_id == "spamcop")
    provider = next(item for item in service.providers if item.id == "spamcop")
    if failure == "unavailable":
        provider.availability = "unavailable"
        provider.unavailable_reason = "temporarily unavailable"
    else:
        service.dns_client.set_response(
            "2.0.0.127.bl.spamcop.net", DNSResponse(state=DNSResponseState.TIMEOUT)
        )
    service.run_once()
    report = scheduler.history_report()
    assert len(report.current_listings) == 4
    assert len(report.unresolved_listings) == 1
    unresolved = report.unresolved_listings[0]
    assert unresolved["provider_id"] == "spamcop"
    assert unresolved["status"] == failure
    assert unresolved["last_known_status"] == "listed"
    assert unresolved["first_detected_at"] == original.first_detected_at.isoformat()
    assert unresolved["reason"] == original.reason
    assert report.delisted_events == 0

    provider.availability = "available"
    service.dns_client.set_response(
        "2.0.0.127.bl.spamcop.net",
        DNSResponse(state=recovery, a_records=["127.0.0.2"] if recovery == DNSResponseState.OK else []),
    )
    service.run_once()
    recovered = scheduler.history_report()
    assert recovered.unresolved_listings == []
    assert len(recovered.current_listings) == (5 if recovery == DNSResponseState.OK else 4)
    assert recovered.delisted_events == (0 if recovery == DNSResponseState.OK else 1)


def test_upgrade_preserves_unlabelled_legacy_history(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'legacy.db'}"
    engine = create_engine(database_url)
    # Build the pre-upgrade schema, without either of the new tables.
    legacy_tables = [table for table in metadata.sorted_tables if table.name not in {
        "blocklist_run_modes", "blocklist_scoped_states"
    }]
    metadata.create_all(engine, tables=legacy_tables)
    now = datetime.now(UTC).replace(tzinfo=None)
    with engine.begin() as connection:
        connection.execute(insert(blocklist_runs).values(
            id="legacy-run", source_filename="old.json", started_at=now,
            completed_at=now, status="completed", total_checks=0,
        ))
        connection.execute(insert(blocklist_states).values(
            asset_id="old", provider_id="spamcop", asset_type="ip", asset_value="127.0.0.2",
            status="listed", first_detected_at=now, last_checked_at=now, last_changed_at=now,
            return_codes_json=["127.0.0.2"], reason="original legacy reason",
        ))
    engine.dispose()
    repository = BlocklistRepository(database_url, dns_mode="live")
    try:
        assert repository.get_run("legacy-run")["dns_mode"] == "legacy"
        assert repository.history_report(30, "default", 3600, 300).total_runs == 0
        legacy = repository.history_report(30, "default", 3600, 300, dns_mode="legacy")
        assert legacy.dns_mode == "legacy"
        assert legacy.total_runs == 1
        assert legacy.current_listings[0]["reason"] == "original legacy reason"
        repository.delete_history_before(datetime.now(UTC) + timedelta(days=1), "default")
        assert repository.get_run("legacy-run") is not None
        with repository.engine.connect() as connection:
            assert connection.execute(select(blocklist_states.c.reason)).scalar_one() == "original legacy reason"
    finally:
        repository.close()


def test_history_api_selects_and_labels_dns_mode(blocklist_service, monkeypatch):
    blocklist_service.run_once()
    monkeypatch.setattr(
        main_module, "get_blocklist_scheduler", lambda: BlocklistScheduler(blocklist_service)
    )
    client = TestClient(main_module.app)
    base = "/api/v1/blocklists/reports/history"
    assert client.get(base).json()["dns_mode"] == "fake"
    assert client.get(base).json()["total_runs"] == 1
    assert client.get(base + "?dns_mode=live").json()["total_runs"] == 0
    assert client.get(base + "?dns_mode=legacy").json()["dns_mode"] == "legacy"
    assert client.get(base + "?dns_mode=invalid").status_code == 422
