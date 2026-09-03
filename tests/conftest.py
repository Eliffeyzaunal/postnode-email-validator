from pathlib import Path

import pytest

from app.config import PROJECT_ROOT, Settings
from app.dns_checker import StaticDNSChecker
from app.models import DNSState
from app.repository import Repository
from app.validator import EmailValidatorService


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "test.db",
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
def service(settings: Settings, dns_checker: StaticDNSChecker) -> EmailValidatorService:
    return EmailValidatorService(settings, Repository(settings.database_path), dns_checker)

