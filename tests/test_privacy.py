from app.privacy import email_hash


def test_email_hash_is_normalized_and_keyed():
    first = email_hash(" User@Example.com ", "first-secret")
    normalized = email_hash("user@example.com", "first-secret")
    different_secret = email_hash("user@example.com", "second-secret")

    assert first == normalized
    assert first != different_secret
    assert len(first) == 64
