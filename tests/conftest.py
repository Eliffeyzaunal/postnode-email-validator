from pathlib import Path

import pytest

from app.config import PROJECT_ROOT, Settings
from app.blocklist.repository import BlocklistRepository
from app.blocklist.service import BlocklistMonitorService
from app.dns_checker import StaticDNSChecker
from app.models import DNSState
from app.repository import Repository
from app.validator import EmailValidatorService


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        disposable_domains_path=PROJECT_ROOT / "data" / "disposable_domains.txt",
        role_accounts_path=PROJECT_ROOT / "data" / "role_accounts.txt",
        domain_typos_path=PROJECT_ROOT / "data" / "domain_typos.json",
        domain_concentration_min_list_size=100,
    )


@pytest.fixture
def dns_checker() -> StaticDNSChecker:
    return StaticDNSChecker({
        "gmail.com": DNSState.MX,
        "example.com": DNSState.MX,
        "mailinator.com": DNSState.MX,
        "gmial.com": DNSState.MX,
        "fallback.example": DNSState.A_FALLBACK,
        "missing.example": DNSState.NXDOMAIN,
        "nomail.example": DNSState.NO_MAIL_HOST,
        "error.example": DNSState.ERROR,
    })


@pytest.fixture
def service(settings: Settings, dns_checker: StaticDNSChecker):
    repository = Repository(settings.database_url)
    try:
        yield EmailValidatorService(settings, repository, dns_checker)
    finally:
        repository.close()


@pytest.fixture
def blocklist_service(tmp_path: Path):
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'blocklist.db').as_posix()}",
        blocklist_providers_path=PROJECT_ROOT / "config" / "blocklists.json",
        blocklist_assets_path=PROJECT_ROOT / "config" / "monitored-assets.example.json",
        blocklist_fake_dns_path=PROJECT_ROOT / "data" / "blocklist_fake_dns.json",
    )
    repository = BlocklistRepository(settings.database_url)
    try:
        yield BlocklistMonitorService(settings, repository)
    finally:
        repository.close()
