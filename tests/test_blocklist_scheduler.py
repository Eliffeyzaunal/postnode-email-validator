from datetime import UTC, datetime, timedelta

import pytest

from app.blocklist.scheduler import BlocklistScheduler


def test_scheduler_records_heartbeat_and_detects_missed_cycle(blocklist_service):
    now = datetime.now(UTC)
    scheduler = BlocklistScheduler(
        blocklist_service,
        interval_seconds=3600,
        grace_seconds=300,
    )

    report = scheduler.run_cycle(now)
    healthy = scheduler.status(now)
    missed = scheduler.status(now + timedelta(seconds=3901))

    assert report.summary.total == 10
    assert healthy.status == "healthy"
    assert healthy.missed is False
    assert healthy.last_success_at == now
    assert missed.status == "missed"
    assert missed.missed is True


def test_scheduler_failure_is_persisted(blocklist_service, monkeypatch):
    scheduler = BlocklistScheduler(blocklist_service, interval_seconds=3600)

    def fail():
        raise RuntimeError("simulated cycle failure")

    monkeypatch.setattr(blocklist_service, "run_once", fail)
    with pytest.raises(RuntimeError, match="simulated cycle failure"):
        scheduler.run_cycle()

    status = scheduler.status()
    assert status.status == "error"
    assert status.missed is False
    assert "simulated cycle failure" in status.last_error


def test_30_day_history_report_contains_provider_metrics(blocklist_service):
    scheduler = BlocklistScheduler(blocklist_service)
    scheduler.run_cycle()
    report = scheduler.history_report(30)

    assert report.days == 30
    assert report.total_runs == 1
    assert report.total_checks == 10
    assert report.notifications == 5
    assert report.listed_events == 5
    assert report.delisted_events == 0
    assert len(report.current_listings) == 5
    spamhaus = next(
        item for item in report.providers if item.provider_id == "spamhaus_zen"
    )
    assert spamhaus.availability_rate == 1.0


def test_history_retention_cannot_be_shorter_than_30_days(blocklist_service):
    with pytest.raises(ValueError, match="en az 30 gün"):
        BlocklistScheduler(blocklist_service, retention_days=29)


def test_scheduler_rejects_zero_interval(blocklist_service):
    with pytest.raises(ValueError, match="en az 1 saniye"):
        BlocklistScheduler(blocklist_service, interval_seconds=0)


def test_scheduler_rejects_negative_grace(blocklist_service):
    with pytest.raises(ValueError, match="negatif olamaz"):
        BlocklistScheduler(blocklist_service, grace_seconds=-1)

def test_history_report_rejects_days_outside_retention(blocklist_service):
    scheduler = BlocklistScheduler(blocklist_service, retention_days=30)

    with pytest.raises(ValueError, match="1 ile 30"):
        scheduler.history_report(0)
    with pytest.raises(ValueError, match="1 ile 30"):
        scheduler.history_report(31)


def test_run_forever_stops_cleanly_after_one_cycle(blocklist_service, monkeypatch):
    from threading import Event

    scheduler = BlocklistScheduler(blocklist_service, interval_seconds=1)
    stop_event = Event()
    calls = []

    def one_cycle():
        calls.append("cycle")
        stop_event.set()

    monkeypatch.setattr(scheduler, "run_cycle", one_cycle)
    scheduler.run_forever(stop_event)

    assert calls == ["cycle"]


def test_run_forever_catches_cycle_failure_and_stops(blocklist_service, monkeypatch, caplog):
    from threading import Event

    scheduler = BlocklistScheduler(blocklist_service, interval_seconds=1)
    stop_event = Event()

    def fail_once():
        stop_event.set()
        raise RuntimeError("simulated loop failure")

    monkeypatch.setattr(scheduler, "run_cycle", fail_once)
    scheduler.run_forever(stop_event)

    assert "simulated loop failure" in caplog.text
