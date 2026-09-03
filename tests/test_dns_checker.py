from dataclasses import dataclass

from app.dns_checker import DNSChecker
from app.models import DNSState
from app.repository import Repository


@dataclass
class MXRecord:
    preference: int
    exchange: str


class ResolverStub:
    def __init__(self, answers):
        self.answers = answers

    def resolve(self, domain: str, record_type: str):
        assert record_type == "MX"
        return self.answers


def test_null_mx_means_domain_accepts_no_email(tmp_path):
    repository = Repository(f"sqlite:///{(tmp_path / 'null-mx.db').as_posix()}")
    checker = DNSChecker(repository)
    checker.resolver = ResolverStub([MXRecord(0, ".")])

    result = checker._lookup_uncached("no-mail.example")

    assert result.state == DNSState.NO_MAIL_HOST
    assert result.detail == "Null MX kaydı bulundu"
    repository.close()


def test_regular_mx_is_accepted(tmp_path):
    repository = Repository(f"sqlite:///{(tmp_path / 'regular-mx.db').as_posix()}")
    checker = DNSChecker(repository)
    checker.resolver = ResolverStub([MXRecord(10, "mail.example.")])

    result = checker._lookup_uncached("example.com")

    assert result.state == DNSState.MX
    repository.close()
