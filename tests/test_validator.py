from app.models import Status
from app.reason_codes import ReasonCode


def test_valid_address(service):
    _, _, item = service.validate_one("user@gmail.com", persist=False)
    assert item.status == Status.VALID
    assert item.reason_codes == [ReasonCode.VALID]


def test_typo_has_suggestion(service):
    _, _, item = service.validate_one("user@gmial.com", persist=False)
    assert item.status == Status.SUSPICIOUS
    assert ReasonCode.DOMAIN_TYPO in item.reason_codes
    assert item.suggestion == "user@gmail.com"


def test_role_and_disposable_are_suspicious(service):
    _, _, results = service.validate_many(["admin@example.com", "user@mailinator.com"], persist=False)
    assert results[0].status == Status.SUSPICIOUS
    assert ReasonCode.ROLE_ACCOUNT in results[0].reason_codes
    assert ReasonCode.DISPOSABLE_DOMAIN in results[1].reason_codes


def test_dns_error_is_not_invalid(service):
    _, _, item = service.validate_one("user@error.example", persist=False)
    assert item.status == Status.SUSPICIOUS
    assert ReasonCode.DNS_LOOKUP_ERROR in item.reason_codes


def test_missing_domain_is_invalid(service):
    _, _, item = service.validate_one("user@missing.example", persist=False)
    assert item.status == Status.INVALID
    assert ReasonCode.DOMAIN_NXDOMAIN in item.reason_codes


def test_each_domain_is_looked_up_once_per_batch(service, dns_checker):
    service.validate_many(["a@gmail.com", "b@gmail.com", "c@example.com"], persist=False)
    assert dns_checker.calls == {"example.com": 1, "gmail.com": 1}


def test_duplicate_and_sequence_detection(service):
    emails = ["same@gmail.com", "same@gmail.com"] + [f"lead{i:03d}@example.com" for i in range(1, 7)]
    _, _, results = service.validate_many(emails, persist=False)
    assert ReasonCode.DUPLICATE_ADDRESS in results[1].reason_codes
    assert all(ReasonCode.GENERATED_SEQUENCE in item.reason_codes for item in results[2:])


def test_database_never_stores_raw_email(service):
    batch_id, _, _ = service.validate_many(["secret.person@gmail.com"])
    stored = service.repository.get_results(batch_id)
    assert "secret.person@gmail.com" not in repr(stored)
    assert stored[0]["masked_email"] == "s***n@gmail.com"
    assert service.repository.get_batch(batch_id) is not None
