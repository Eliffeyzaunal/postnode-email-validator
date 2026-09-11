from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from app.blocklist.models import (
    BlocklistCheckRequest,
    CheckStatus,
    DNSResponse,
    DNSResponseState,
    MonitoredAsset,
)


def test_official_examples_are_checked_with_fake_dns(blocklist_service):
    report = blocklist_service.run_once()

    assert report.summary.model_dump() == {
        "total": 10,
        "listed": 5,
        "not_listed": 2,
        "query_error": 0,
        "unavailable": 3,
    }
    assert len(report.notifications) == 5
    assert {item.type.value for item in report.notifications} == {"listed"}
    assert any("Spamhaus resmi pozitif" in (item.reason or "") for item in report.notifications)
    assert all(item.status != CheckStatus.QUERY_ERROR for item in report.results)


def test_same_result_does_not_create_duplicate_notifications(blocklist_service):
    first = blocklist_service.run_once()
    second = blocklist_service.run_once()

    assert len(first.notifications) == 5
    assert second.notifications == []


def test_delisting_creates_transition_notification(blocklist_service):
    blocklist_service.run_once()
    blocklist_service.dns_client.set_response(
        "2.0.0.127.bl.spamcop.net",
        DNSResponse(state=DNSResponseState.NXDOMAIN),
    )

    report = blocklist_service.run_once()
    events = [item for item in report.notifications if item.type.value == "delisted"]

    assert len(events) == 1
    assert events[0].provider_id == "spamcop"
    assert events[0].previous_status == CheckStatus.LISTED
    assert events[0].current_status == CheckStatus.NOT_LISTED
    assert events[0].first_detected_at is not None
    assert events[0].reason == "SpamCop resmi DNSBL test girdisi"


def test_query_error_does_not_hide_a_later_delisting(blocklist_service):
    first = blocklist_service.run_once()
    first_listing = next(
        item for item in first.notifications if item.provider_id == "spamcop"
    )
    blocklist_service.dns_client.set_response(
        "2.0.0.127.bl.spamcop.net",
        DNSResponse(state=DNSResponseState.TIMEOUT, detail="DNS zaman aşımı"),
    )

    failed = blocklist_service.run_once()
    failed_event = next(
        item for item in failed.notifications if item.provider_id == "spamcop"
    )
    assert failed_event.type.value == "query_error"

    blocklist_service.dns_client.set_response(
        "2.0.0.127.bl.spamcop.net",
        DNSResponse(state=DNSResponseState.NXDOMAIN),
    )
    recovered = blocklist_service.run_once()
    event = next(
        item for item in recovered.notifications if item.provider_id == "spamcop"
    )

    assert event.type.value == "delisted"
    assert event.previous_status == CheckStatus.QUERY_ERROR
    assert event.current_status == CheckStatus.NOT_LISTED
    assert event.first_detected_at == first_listing.first_detected_at
    assert event.reason == "SpamCop resmi DNSBL test girdisi"


def test_query_error_recovery_does_not_repeat_listed_alarm(blocklist_service):
    first = blocklist_service.run_once()
    first_listing = next(
        item for item in first.notifications if item.provider_id == "spamcop"
    )
    blocklist_service.dns_client.set_response(
        "2.0.0.127.bl.spamcop.net",
        DNSResponse(state=DNSResponseState.TIMEOUT, detail="DNS zaman aşımı"),
    )
    blocklist_service.run_once()
    blocklist_service.dns_client.set_response(
        "2.0.0.127.bl.spamcop.net",
        DNSResponse(
            state=DNSResponseState.OK,
            a_records=["127.0.0.2"],
            txt_records=["SpamCop resmi DNSBL test girdisi"],
        ),
    )

    recovered = blocklist_service.run_once()
    event = next(
        item for item in recovered.notifications if item.provider_id == "spamcop"
    )

    assert event.type.value == "recovered"
    assert event.current_status == CheckStatus.LISTED
    assert event.first_detected_at == first_listing.first_detected_at


def test_asset_id_cannot_be_reused_for_a_different_value(blocklist_service):
    blocklist_service.run_once()
    request = BlocklistCheckRequest(
        assets=[
            MonitoredAsset(
                id="spamhaus-test-ip",
                type="ip",
                value="127.0.0.3",
            )
        ]
    )

    with pytest.raises(ValueError, match="daha önce farklı"):
        blocklist_service.run_once(request)


def test_concurrent_runs_create_one_alarm_set(blocklist_service):
    barrier = Barrier(2)

    def run_check():
        barrier.wait()
        return blocklist_service.run_once()

    with ThreadPoolExecutor(max_workers=2) as pool:
        reports = list(pool.map(lambda _item: run_check(), range(2)))

    listed_notifications = [
        notification
        for report in reports
        for notification in report.notifications
        if notification.type.value == "listed"
    ]
    assert len(listed_notifications) == 5


def test_run_and_notifications_are_persisted(blocklist_service):
    report = blocklist_service.run_once()
    stored = blocklist_service.repository.get_run(report.run_id)
    notifications = blocklist_service.repository.get_notifications(report.run_id)

    assert stored is not None
    assert stored["total_checks"] == 10
    assert len(stored["results"]) == 10
    assert len(notifications) == 5

def test_service_rejects_repository_dns_mode_mismatch(blocklist_service):
    from types import SimpleNamespace
    from app.blocklist.service import BlocklistMonitorService

    wrong_mode = "live" if blocklist_service.settings.blocklist_dns_mode != "live" else "fake"
    repository = SimpleNamespace(dns_mode=wrong_mode)

    with pytest.raises(ValueError, match="DNS modu aynı"):
        BlocklistMonitorService(blocklist_service.settings, repository=repository)


def test_service_rejects_empty_asset_request(blocklist_service):
    request = BlocklistCheckRequest(assets=[])

    with pytest.raises(ValueError, match="En az bir"):
        blocklist_service.run_once(request)


def test_service_rejects_duplicate_asset_ids(blocklist_service):
    request = BlocklistCheckRequest(
        assets=[
            MonitoredAsset(id="same-id", type="ip", value="127.0.0.2"),
            MonitoredAsset(id="same-id", type="ip", value="127.0.0.3"),
        ]
    )

    with pytest.raises(ValueError, match="benzersiz"):
        blocklist_service.run_once(request)


def test_provider_status_exposes_configuration(blocklist_service):
    statuses = blocklist_service.provider_status()

    assert statuses
    assert all("id" in item for item in statuses)
    assert all("availability" in item for item in statuses)
    assert all("asset_types" in item for item in statuses)
