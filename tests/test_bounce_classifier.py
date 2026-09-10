import json
from pathlib import Path

import pytest

from app.bounce_classifier.classifier import EventClassifier
from app.bounce_classifier.models import EventCategory
from app.bounce_classifier.rules import rule_matches
from app.config import PROJECT_ROOT

RULE_COUNT = len(EventClassifier(PROJECT_ROOT / "config" / "bounce_rules.json").rules)


@pytest.fixture(scope="module")
def classifier() -> EventClassifier:
    return EventClassifier(PROJECT_ROOT / "config" / "bounce_rules.json")


@pytest.mark.parametrize("rule_index", range(RULE_COUNT))
def test_every_rule_has_working_trigger_and_counter_example(
    classifier: EventClassifier,
    rule_index: int,
):
    rule = classifier.rules[rule_index]
    assert rule_matches(rule, classifier.normalize(rule.trigger_example))
    assert not rule_matches(rule, classifier.normalize(rule.counter_example))


@pytest.mark.parametrize("rule_index", range(RULE_COUNT))
def test_every_rule_trigger_is_selected_by_the_active_priority_order(
    classifier: EventClassifier,
    rule_index: int,
):
    rule = classifier.rules[rule_index]
    assert classifier.classify(rule.trigger_example).rule_id == rule.rule_id


def test_rule_count_stays_in_sync_with_parametrized_contract(classifier: EventClassifier):
    assert len(classifier.rules) == 22


def test_blocklist_rule_takes_precedence_over_generic_policy(classifier: EventClassifier):
    result = classifier.classify({
        "event_id": "evt-blocklist",
        "provider": "gmail",
        "enhanced_status": "5.7.1",
        "diagnostic_code": "550 5.7.1 rejected because IP is listed on Spamhaus",
    })
    assert result.category == EventCategory.BLOCKLIST_REJECTION
    assert result.rule_id == "blocklist_rejection_message"


def test_native_ses_event_is_normalized_without_leaking_email(classifier: EventClassifier):
    event = {
        "notificationType": "Bounce",
        "mail": {"messageId": "safe-event-id", "destination": ["alice@example.com"]},
        "bounce": {
            "bounceType": "Permanent",
            "bounceSubType": "General",
            "bouncedRecipients": [{
                "emailAddress": "alice@example.com",
                "status": "5.1.1",
                "diagnosticCode": "smtp; 550 5.1.1 alice@example.com user unknown",
            }],
        },
    }
    result = classifier.classify(event)
    payload = result.model_dump_json()
    assert result.category == EventCategory.PERMANENT_INVALID_ADDRESS
    assert result.recipient_domain == "example.com"
    assert len(result.recipient_hash or "") == 64
    assert "alice@example.com" not in payload
    assert "diagnostic" not in payload


@pytest.mark.parametrize(
    ("feedback_type", "expected_rule", "permanence"),
    [
        ("not-spam", "complaint_not_spam", "neutral"),
        ("auth-failure", "complaint_auth_failure", "neutral"),
        ("abuse", "complaint_event", "permanent"),
    ],
)
def test_complaint_feedback_subtypes_have_safe_actions(
    classifier: EventClassifier,
    feedback_type: str,
    expected_rule: str,
    permanence: str,
):
    result = classifier.classify({"event_type": "complaint", "feedback_type": feedback_type})
    assert result.rule_id == expected_rule
    assert result.permanence.value == permanence


def test_event_id_cannot_leak_an_email(classifier: EventClassifier):
    result = classifier.classify({
        "event_id": "private@example.com",
        "diagnostic_code": "599 unknown",
    })
    assert result.event_id.startswith("hmac-sha256:")
    assert "private@example.com" not in result.model_dump_json()


def test_long_event_ids_are_hashed_without_recipient_suffix_collisions(classifier: EventClassifier):
    event = {
        "event_id": "x" * 250,
        "bounce": {
            "bouncedRecipients": [
                {"emailAddress": "one@example.com", "status": "4.2.2"},
                {"emailAddress": "two@example.net", "status": "5.1.1"},
            ]
        },
    }
    results = classifier.classify_many([event]).results
    assert len({result.event_id for result in results}) == 2
    assert all(result.event_id.startswith("hmac-sha256:") for result in results)


@pytest.mark.parametrize(
    ("event_id", "diagnostic"),
    [
        ("person@localhost", "599 failed for person@localhost"),
        ("üye@example.com", "599 failed for üye@example.com"),
        ('"person name"@example.com', '599 failed for "person name"@example.com'),
    ],
)
def test_nonstandard_email_shapes_are_redacted(
    classifier: EventClassifier,
    event_id: str,
    diagnostic: str,
):
    result = classifier.classify({"event_id": event_id, "diagnostic_code": diagnostic})
    payload = result.model_dump_json()
    assert result.event_id.startswith("hmac-sha256:")
    assert event_id not in payload
    assert "@" not in result.unknown_pattern


def test_recipient_hmac_uses_configured_secret():
    event = {"recipient": "private@example.org", "diagnostic_code": "599 unknown"}
    first = EventClassifier(hash_secret="first-secret").classify(event)
    second = EventClassifier(hash_secret="second-secret").classify(event)
    assert first.recipient_hash != second.recipient_hash


def test_untrusted_identity_fields_cannot_leak_emails(classifier: EventClassifier):
    result = classifier.classify({
        "event_id": "safe",
        "recipient_hash": "hash@example.com",
        "recipient_domain": "owner@example.org",
        "provider": "provider@example.net",
        "diagnostic_code": "599 unknown",
    })
    payload = result.model_dump_json()
    assert result.recipient_domain == "example.org"
    assert len(result.recipient_hash or "") == 64
    assert result.provider == "unknown"
    assert "@" not in payload


def test_invalid_recipient_domain_is_not_returned(classifier: EventClassifier):
    result = classifier.classify({
        "recipient": "person@bad domain",
        "diagnostic_code": "599 unknown",
    })
    assert result.recipient_domain is None


def test_malformed_native_containers_are_tolerated(classifier: EventClassifier):
    result = classifier.classify({
        "mail": "not-an-object",
        "bounce": "not-an-object",
        "complaint": [],
        "diagnostic_code": "599 unknown",
    })
    assert result.category == EventCategory.UNKNOWN


def test_unknown_pattern_is_safe_and_actionable(classifier: EventClassifier):
    result = classifier.classify({
        "event_id": "evt-unknown",
        "recipient": "private.person@example.org",
        "diagnostic_code": "599 vendor code 123456 for private.person@example.org from 192.0.2.5",
    })
    assert result.category == EventCategory.UNKNOWN
    assert result.unknown_pattern == "599 vendor code <id> for <email> from <ip>"
    assert "private.person@example.org" not in result.model_dump_json()


def test_custom_rule_can_be_added_without_python_change(tmp_path: Path):
    source = json.loads((PROJECT_ROOT / "config" / "bounce_rules.json").read_text())
    source["rules"].insert(0, {
        "id": "custom_vendor_rule",
        "priority": 1,
        "category": "temporary_server_error",
        "category_label": "Gecici sunucu hatasi",
        "subreason": "Ozel saglayici bakimi",
        "action": "Bir saat sonra yeniden dene",
        "confidence": "high",
        "permanence": "transient",
        "providers": ["corporate"],
        "sources": ["https://www.rfc-editor.org/rfc/rfc3463.html"],
        "match": {"diagnostic_regex": "vendor-maintenance-42"},
        "example_message": "451 vendor-maintenance-42",
        "trigger_example": {"diagnostic_code": "451 vendor-maintenance-42"},
        "counter_example": {"diagnostic_code": "451 vendor-maintenance-41"},
    })
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    result = EventClassifier(path).classify({"diagnostic_code": "451 vendor-maintenance-42"})
    assert result.rule_id == "custom_vendor_rule"


def test_unknown_match_field_is_rejected_instead_of_matching_every_event(tmp_path: Path):
    source = json.loads((PROJECT_ROOT / "config" / "bounce_rules.json").read_text())
    source["rules"][0]["match"] = {"diagnostic_regx": "misspelled"}
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(ValueError, match="Desteklenmeyen eslesme alani"):
        EventClassifier(path)


def test_shadowed_rule_trigger_is_rejected_at_startup(tmp_path: Path):
    source = json.loads((PROJECT_ROOT / "config" / "bounce_rules.json").read_text())
    source["rules"].insert(1, {
        "id": "shadowed_not_spam",
        "priority": 6,
        "category": "complaint",
        "category_label": "Test",
        "subreason": "Test",
        "action": "Test",
        "confidence": "high",
        "permanence": "neutral",
        "providers": ["ses"],
        "sources": ["https://docs.aws.amazon.com/ses/latest/dg/notification-contents.html"],
        "match": {"event_types": ["complaint"], "feedback_types": ["not-spam"]},
        "example_message": "Complaint / not-spam",
        "trigger_example": {"event_type": "complaint", "feedback_type": "not-spam"},
        "counter_example": {"event_type": "bounce"},
    })
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(ValueError, match="golgeleniyor"):
        EventClassifier(path)


def test_sns_wrapped_ses_event_is_supported_without_leaking_email(classifier: EventClassifier):
    inner = {
        "notificationType": "Bounce",
        "bounce": {
            "bounceType": "Permanent",
            "bounceSubType": "General",
            "bouncedRecipients": [{
                "emailAddress": "private@example.com",
                "status": "5.1.1",
                "diagnosticCode": "550 private@example.com user unknown",
            }],
        },
    }
    event = {"Type": "Notification", "MessageId": "sns-1", "Message": json.dumps(inner)}
    result = classifier.classify(event)
    assert result.event_id == "sns-1"
    assert result.category == EventCategory.PERMANENT_INVALID_ADDRESS
    assert "private@example.com" not in result.model_dump_json()


def test_multi_recipient_ses_notification_is_expanded_in_batch(classifier: EventClassifier):
    event = {
        "notificationType": "Bounce",
        "mail": {"messageId": "ses-1"},
        "bounce": {
            "bounceType": "Permanent",
            "bounceSubType": "General",
            "bouncedRecipients": [
                {
                    "emailAddress": "full@example.com",
                    "status": "4.2.2",
                    "diagnosticCode": "452 mailbox full",
                },
                {
                    "emailAddress": "gone@example.net",
                    "status": "5.1.1",
                    "diagnosticCode": "550 user unknown",
                },
            ],
        },
    }
    with pytest.raises(ValueError, match="Birden fazla"):
        classifier.classify(event)
    response = classifier.classify_many([event])
    assert response.total == 2
    assert [result.event_id for result in response.results] == [
        "ses-1:recipient:1",
        "ses-1:recipient:2",
    ]
    assert [result.category for result in response.results] == [
        EventCategory.MAILBOX_FULL,
        EventCategory.PERMANENT_INVALID_ADDRESS,
    ]


def test_batch_summary_reports_unknown_rate(classifier: EventClassifier):
    response = classifier.classify_many([
        {"event_type": "complaint"},
        {"diagnostic_code": "unrecognized vendor response"},
    ])
    assert response.total == 2
    assert response.category_counts == {"complaint": 1, "unknown": 1}
    assert response.unknown_rate == 0.5
