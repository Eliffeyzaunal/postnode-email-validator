from app.bounce_classifier.privacy import (
    message_fingerprint,
    safe_event_id,
    safe_message_pattern,
    safe_recipient_identity,
)


def test_safe_message_pattern_redacts_email_ip_and_long_ids():
    value = (
        'Failure for "Person Name"@Example.COM from 192.0.2.55 '
        'message 123456789 and ABCDEF1234567890'
    )

    pattern = safe_message_pattern(value)

    assert "@example.com" not in pattern
    assert "192.0.2.55" not in pattern
    assert "123456789" not in pattern
    assert "abcdef1234567890" not in pattern
    assert "<email>" in pattern
    assert "<ip>" in pattern
    assert "<id>" in pattern


def test_safe_message_pattern_collapses_whitespace_and_caps_length():
    value = "  SOME\n\tTEXT   HERE  "

    assert safe_message_pattern(value, max_length=9) == "some text"


def test_message_fingerprint_is_stable_after_redaction():
    first = message_fingerprint("550 user@example.com from 192.0.2.1")
    second = message_fingerprint("550 other@example.net from 203.0.113.9")

    assert first == second
    assert len(first) == 64


def test_safe_event_id_keeps_safe_ids_and_hashes_unsafe_ids():
    assert safe_event_id("evt-123_OK:part.1", "secret") == "evt-123_OK:part.1"

    hashed = safe_event_id("private@example.com", "secret")
    assert hashed.startswith("hmac-sha256:")
    assert "private@example.com" not in hashed


def test_safe_recipient_identity_accepts_supplied_sha256_hash():
    supplied = "a" * 64
    digest, domain = safe_recipient_identity(
        {
            "recipient_hash": supplied.upper(),
            "recipient_domain": "Example.COM.",
        },
        "secret",
    )

    assert digest == supplied
    assert domain == "example.com"


def test_safe_recipient_identity_hashes_untrusted_supplied_hash():
    digest, domain = safe_recipient_identity(
        {
            "recipient_hash": "not-a-hash",
            "recipient_domain": "example.com",
        },
        "secret",
    )

    assert digest is not None
    assert digest != "not-a-hash"
    assert len(digest) == 64
    assert domain == "example.com"


def test_safe_recipient_identity_reads_complaint_recipient():
    digest, domain = safe_recipient_identity(
        {
            "complaint": {
                "complainedRecipients": [
                    {"emailAddress": "complainer@Example.ORG"}
                ]
            }
        },
        "secret",
    )

    assert digest is not None
    assert len(digest) == 64
    assert domain == "example.org"


def test_safe_recipient_identity_reads_mail_destination():
    digest, domain = safe_recipient_identity(
        {"mail": {"destination": ["person@Example.NET"]}},
        "secret",
    )

    assert digest is not None
    assert domain == "example.net"


def test_safe_recipient_identity_returns_none_without_identity():
    assert safe_recipient_identity({}, "secret") == (None, None)


def test_invalid_supplied_domain_is_dropped():
    digest, domain = safe_recipient_identity(
        {"recipient_hash": "b" * 64, "recipient_domain": "bad domain"},
        "secret",
    )

    assert digest == "b" * 64
    assert domain is None
