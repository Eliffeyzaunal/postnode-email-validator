from app.blocklist.models import CheckStatus, DNSResponse, DNSResponseState


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


def test_run_and_notifications_are_persisted(blocklist_service):
    report = blocklist_service.run_once()
    stored = blocklist_service.repository.get_run(report.run_id)
    notifications = blocklist_service.repository.get_notifications(report.run_id)

    assert stored is not None
    assert stored["total_checks"] == 10
    assert len(stored["results"]) == 10
    assert len(notifications) == 5
