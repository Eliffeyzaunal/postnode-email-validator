import json

import pytest

from app.bounce_classifier.models import NormalizedEvent
from app.bounce_classifier.rules import load_rules, rule_matches


def write_rules(tmp_path, payload):
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def valid_rule(**overrides):
    rule = {
        "id": "r1",
        "priority": 10,
        "category": "unknown",
        "category_label": "Unknown",
        "subreason": "Reason",
        "action": "Review",
        "confidence": "low",
        "permanence": "unknown",
        "providers": ["ses"],
        "sources": ["https://example.com"],
        "match": {"event_types": ["bounce"]},
        "example_message": "example",
        "trigger_example": {"event_type": "bounce"},
        "counter_example": {"event_type": "complaint"},
    }
    rule.update(overrides)
    return rule


@pytest.mark.parametrize(
    "payload, message",
    [
        ([], "rules listesi"),
        ({"schema_version": 2, "rules": []}, "schema_version 1"),
        ({"schema_version": 1, "rules": ["bad"]}, "JSON nesnesi"),
    ],
)
def test_load_rules_rejects_invalid_root_shapes(tmp_path, payload, message):
    with pytest.raises(ValueError, match=message):
        load_rules(write_rules(tmp_path, payload))


def test_load_rules_rejects_duplicate_ids(tmp_path):
    first = valid_rule()
    second = valid_rule(priority=20)

    with pytest.raises(ValueError, match="Yinelenen kural kimligi"):
        load_rules(write_rules(tmp_path, {"schema_version": 1, "rules": [first, second]}))


def test_load_rules_rejects_duplicate_priorities(tmp_path):
    first = valid_rule()
    second = valid_rule(id="r2")

    with pytest.raises(ValueError, match="Yinelenen kural onceligi"):
        load_rules(write_rules(tmp_path, {"schema_version": 1, "rules": [first, second]}))


@pytest.mark.parametrize(
    "match_value, message",
    [
        ({}, "en az bir eslesme"),
        ({"event_types": []}, "bos olmayan bir metin listesi"),
        ({"event_types": [""]}, "bos olmayan bir metin listesi"),
        ({"diagnostic_regex": ""}, "bos olmayan bir regex"),
    ],
)
def test_load_rules_rejects_invalid_match_values(tmp_path, match_value, message):
    rule = valid_rule(match=match_value)

    with pytest.raises(ValueError, match=message):
        load_rules(write_rules(tmp_path, {"schema_version": 1, "rules": [rule]}))


@pytest.mark.parametrize("field", ["providers", "sources"])
def test_load_rules_requires_nonempty_provider_and_source_lists(tmp_path, field):
    rule = valid_rule(**{field: []})

    with pytest.raises(ValueError, match=field):
        load_rules(write_rules(tmp_path, {"schema_version": 1, "rules": [rule]}))


@pytest.mark.parametrize("field", ["category_label", "subreason", "action", "example_message"])
def test_load_rules_requires_nonempty_text_fields(tmp_path, field):
    rule = valid_rule(**{field: " "})

    with pytest.raises(ValueError, match=field):
        load_rules(write_rules(tmp_path, {"schema_version": 1, "rules": [rule]}))


@pytest.mark.parametrize("field", ["trigger_example", "counter_example"])
def test_load_rules_requires_example_objects(tmp_path, field):
    rule = valid_rule(**{field: "not-an-object"})

    with pytest.raises(ValueError, match=field):
        load_rules(write_rules(tmp_path, {"schema_version": 1, "rules": [rule]}))


def test_load_rules_rejects_empty_rules_list(tmp_path):
    with pytest.raises(ValueError, match="en az bir kural"):
        load_rules(write_rules(tmp_path, {"schema_version": 1, "rules": []}))


def test_rule_matches_honors_positive_and_negative_diagnostic_regex():
    event = NormalizedEvent(
        event_id="evt",
        event_type="bounce",
        bounce_type="",
        bounce_subtype="",
        smtp_code="550",
        enhanced_status="5.7.1",
        diagnostic="550 blocked by policy",
        feedback_type="",
        provider="gmail",
        recipient_hash=None,
        recipient_domain=None,
    )
    positive = valid_rule(
        match={
            "event_types": ["BOUNCE"],
            "enhanced_status_prefixes": ["5.7"],
            "diagnostic_regex": "blocked",
            "diagnostic_not_regex": "allowlisted",
        }
    )
    path_payload = {"schema_version": 1, "rules": [positive]}

    # load_rules also compiles the regexes and gives us a real ClassificationRule.
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "rules.json"
        path.write_text(json.dumps(path_payload), encoding="utf-8")
        rule = load_rules(path)[0]

    assert rule_matches(rule, event) is True

    from dataclasses import replace

    allowlisted_event = replace(event, diagnostic="550 blocked but allowlisted")
    assert rule_matches(rule, allowlisted_event) is False
