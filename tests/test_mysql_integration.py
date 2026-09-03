import os
import uuid

import pytest

from app.config import PROJECT_ROOT, Settings
from app.dns_checker import StaticDNSChecker
from app.models import DNSState
from app.repository import Repository
from app.validator import EmailValidatorService


MYSQL_URL = os.getenv("TEST_MYSQL_DATABASE_URL")


@pytest.mark.skipif(not MYSQL_URL, reason="MySQL entegrasyon adresi tanımlı değil.")
def test_mysql_repository_round_trip():
    settings = Settings(
        database_url=MYSQL_URL,
        disposable_domains_path=PROJECT_ROOT / "data" / "disposable_domains.txt",
        role_accounts_path=PROJECT_ROOT / "data" / "role_accounts.txt",
        domain_typos_path=PROJECT_ROOT / "data" / "domain_typos.json",
    )
    repository = Repository(settings.database_url)
    service = EmailValidatorService(
        settings,
        repository,
        StaticDNSChecker({"gmail.com": DNSState.MX}),
    )
    batch_id = ""
    try:
        raw_email = f"integration-{uuid.uuid4().hex[:10]}@gmail.com"
        batch_id, summary, _ = service.validate_many(
            [raw_email],
            filename="mysql-integration.csv",
        )
        metadata = repository.get_batch(batch_id)
        stored = repository.get_results(batch_id)

        assert summary["total"] == 1
        assert metadata is not None
        assert metadata["filename"] == "mysql-integration.csv"
        assert len(stored) == 1
        assert stored[0]["status"] == "gecerli"
        assert stored[0]["masked_email"].endswith("@gmail.com")
        assert raw_email not in repr(stored)
    finally:
        repository.delete_batches([batch_id] if batch_id else [])
        repository.close()
