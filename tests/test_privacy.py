from app.privacy import email_hash, mask_email


def test_email_hash_is_normalized_and_keyed():
    first = email_hash(" User@Example.com ", "first-secret")
    normalized = email_hash("user@example.com", "first-secret")
    different_secret = email_hash("user@example.com", "second-secret")

    assert first == normalized
    assert first != different_secret
    assert len(first) == 64

def test_mask_email_hides_missing_or_malformed_values():
    assert mask_email(None) == "***"
    assert mask_email("") == "***"
    assert mask_email("not-an-email") == "***"


def test_mask_email_handles_empty_local_part():
    assert mask_email("@Example.COM") == "***@example.com"


def test_mask_email_handles_single_character_local_part():
    assert mask_email("A@Example.COM") == "A***@example.com"


def test_mask_email_keeps_only_first_and_last_local_characters():
    assert mask_email("Alice@Example.COM") == "A***e@example.com"


def test_mask_email_uses_last_at_sign_and_casefolds_domain():
    assert mask_email("odd@local@Example.COM") == "o***l@example.com"
