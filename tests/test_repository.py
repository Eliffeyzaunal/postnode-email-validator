from datetime import UTC, datetime, timedelta

import pytest

import app.repository as repository_module
from app.models import DNSResult, DNSState, InternalResult, Status
from app.reason_codes import ReasonCode
from app.repository import Repository, _iso_utc, _utc_naive


def make_repository(tmp_path, name: str = "repository.db") -> Repository:
    return Repository(
        f"sqlite:///{(tmp_path / name).as_posix()}",
        email_hash_secret="test-secret",
    )


def test_repository_ping_and_missing_batch(tmp_path):
    repository = make_repository(tmp_path)
    try:
        repository.ping()
        assert repository.get_batch("missing") is None
        assert repository.get_results("missing") == []
    finally:
        repository.close()


def test_save_batch_round_trip_masks_sensitive_values_and_cascades_delete(tmp_path):
    repository = make_repository(tmp_path)
    result = InternalResult(
        row_number=1,
        original=" User@Example.com ",
        normalized="user@example.com",
        domain="example.com",
        local_part="user",
        status=Status.SUSPICIOUS,
        reason_codes=[ReasonCode.DOMAIN_TYPO],
        suggestion="user@gmail.com",
    )

    try:
        repository.save_batch(
            "batch-1",
            "input.csv",
            {"total": 1, "valid": 0, "suspicious": 1, "invalid": 0},
            [result],
        )

        metadata = repository.get_batch("batch-1")
        stored = repository.get_results("batch-1")

        assert metadata is not None
        assert metadata["batch_id"] == "batch-1"
        assert metadata["filename"] == "input.csv"
        assert metadata["created_at"].endswith("Z")
        assert metadata["summary"]["total"] == 1

        assert len(stored) == 1
        assert stored[0]["masked_email"] == "u***r@example.com"
        assert stored[0]["email_hash"] != "user@example.com"
        assert stored[0]["domain"] == "example.com"
        assert stored[0]["status"] == "supheli"
        assert stored[0]["reason_codes"] == ["DOMAIN_TYPO"]
        assert stored[0]["suggestion"] == "u***r@gmail.com"

        assert repository.count_results_for_batches(["batch-1"]) == 1
        assert repository.count_results_for_batches([]) == 0

        repository.delete_batches([])
        repository.delete_batches(["batch-1"])
        assert repository.get_batch("batch-1") is None
        assert repository.count_results_for_batches(["batch-1"]) == 0
    finally:
        repository.close()


def test_save_empty_batch_does_not_insert_result_rows(tmp_path):
    repository = make_repository(tmp_path, "empty-batch.db")
    try:
        repository.save_batch(
            "empty-batch",
            None,
            {"total": 0, "valid": 0, "suspicious": 0, "invalid": 0},
            [],
        )
        assert repository.get_batch("empty-batch") is not None
        assert repository.get_results("empty-batch") == []
    finally:
        repository.delete_batches(["empty-batch"])
        repository.close()


def test_dns_cache_upsert_expiry_and_delete(tmp_path):
    repository = make_repository(tmp_path, "dns-cache.db")
    now = datetime.now(UTC)

    try:
        repository.put_dns(
            DNSResult("example.com", DNSState.MX, "first"),
            now,
            now + timedelta(hours=1),
        )
        first = repository.get_cached_dns("example.com")
        assert first is not None
        assert first.state == DNSState.MX
        assert first.detail == "first"
        assert first.from_cache is True

        repository.put_dns(
            DNSResult("example.com", DNSState.ERROR, "updated"),
            now,
            now + timedelta(minutes=5),
        )
        updated = repository.get_cached_dns("example.com")
        assert updated is not None
        assert updated.state == DNSState.ERROR
        assert updated.detail == "updated"

        repository.put_dns(
            DNSResult("expired.example", DNSState.MX, "expired"),
            now - timedelta(hours=2),
            now - timedelta(hours=1),
        )
        assert repository.get_cached_dns("expired.example") is None

        repository.delete_dns_entries([])
        repository.delete_dns_entries(["example.com", "expired.example"])
        assert repository.get_cached_dns("example.com") is None
    finally:
        repository.close()


def test_datetime_helpers_cover_naive_and_aware_inputs():
    naive = datetime(2026, 9, 11, 12, 0, 0)
    aware = datetime(2026, 9, 11, 12, 0, 0, tzinfo=UTC)

    assert _utc_naive(naive) is naive
    assert _utc_naive(aware).tzinfo is None
    assert _iso_utc(naive) == "2026-09-11T12:00:00Z"


def test_unsupported_database_backend_is_rejected(monkeypatch):
    class UnsupportedEngine:
        class Dialect:
            name = "postgresql"

        dialect = Dialect()

    monkeypatch.setattr(
        repository_module,
        "create_engine",
        lambda *args, **kwargs: UnsupportedEngine(),
    )

    with pytest.raises(ValueError, match="Yalnızca MySQL"):
        Repository("postgresql://example.invalid/db")
