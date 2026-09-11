from dataclasses import dataclass

import dns.exception
import dns.resolver

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


class ResolverPlan:
    def __init__(self, responses):
        self.responses = responses
        self.calls: list[str] = []

    def resolve(self, domain: str, record_type: str):
        self.calls.append(record_type)
        response = self.responses[record_type]
        if isinstance(response, BaseException):
            raise response
        return response


def build_checker(tmp_path, name: str, responses) -> DNSChecker:
    repository = Repository(f"sqlite:///{(tmp_path / name).as_posix()}")
    checker = DNSChecker(repository)
    checker.resolver = ResolverPlan(responses)
    return checker


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


def test_mx_noanswer_falls_back_to_a(tmp_path):
    checker = build_checker(
        tmp_path,
        "a-fallback.db",
        {"MX": dns.resolver.NoAnswer(), "A": [object()], "AAAA": dns.resolver.NoAnswer()},
    )
    try:
        result = checker._lookup_uncached("fallback.example")
        assert result.state == DNSState.A_FALLBACK
        assert result.detail == "A kaydı bulundu"
        assert checker.resolver.calls == ["MX", "A"]
    finally:
        checker.repository.close()


def test_mx_and_a_noanswer_fall_back_to_aaaa(tmp_path):
    checker = build_checker(
        tmp_path,
        "aaaa-fallback.db",
        {"MX": dns.resolver.NoAnswer(), "A": dns.resolver.NoAnswer(), "AAAA": [object()]},
    )
    try:
        result = checker._lookup_uncached("ipv6-mail.example")
        assert result.state == DNSState.A_FALLBACK
        assert result.detail == "AAAA kaydı bulundu"
        assert checker.resolver.calls == ["MX", "A", "AAAA"]
    finally:
        checker.repository.close()


def test_no_mx_a_or_aaaa_means_no_mail_host(tmp_path):
    checker = build_checker(
        tmp_path,
        "no-mail-host.db",
        {
            "MX": dns.resolver.NoAnswer(),
            "A": dns.resolver.NoAnswer(),
            "AAAA": dns.resolver.NoAnswer(),
        },
    )
    try:
        result = checker._lookup_uncached("nomail.example")
        assert result.state == DNSState.NO_MAIL_HOST
        assert result.detail == "MX, A ve AAAA kaydı yok"
    finally:
        checker.repository.close()


def test_nxdomain_from_mx_is_definitive(tmp_path):
    checker = build_checker(
        tmp_path,
        "mx-nxdomain.db",
        {"MX": dns.resolver.NXDOMAIN(), "A": dns.resolver.NoAnswer(), "AAAA": dns.resolver.NoAnswer()},
    )
    try:
        result = checker._lookup_uncached("missing.example")
        assert result.state == DNSState.NXDOMAIN
        assert checker.resolver.calls == ["MX"]
    finally:
        checker.repository.close()


def test_timeout_from_mx_is_technical_error(tmp_path):
    checker = build_checker(
        tmp_path,
        "mx-timeout.db",
        {
            "MX": dns.exception.Timeout(timeout=1.0),
            "A": dns.resolver.NoAnswer(),
            "AAAA": dns.resolver.NoAnswer(),
        },
    )
    try:
        result = checker._lookup_uncached("slow.example")
        assert result.state == DNSState.ERROR
        assert result.detail == "Timeout"
        assert checker.resolver.calls == ["MX"]
    finally:
        checker.repository.close()


def test_generic_dns_exception_from_mx_is_technical_error(tmp_path):
    checker = build_checker(
        tmp_path,
        "mx-error.db",
        {
            "MX": dns.exception.DNSException("boom"),
            "A": dns.resolver.NoAnswer(),
            "AAAA": dns.resolver.NoAnswer(),
        },
    )
    try:
        result = checker._lookup_uncached("broken.example")
        assert result.state == DNSState.ERROR
        assert result.detail == "DNSException"
    finally:
        checker.repository.close()


def test_nxdomain_during_a_fallback_is_definitive(tmp_path):
    checker = build_checker(
        tmp_path,
        "a-nxdomain.db",
        {"MX": dns.resolver.NoAnswer(), "A": dns.resolver.NXDOMAIN(), "AAAA": dns.resolver.NoAnswer()},
    )
    try:
        result = checker._lookup_uncached("gone.example")
        assert result.state == DNSState.NXDOMAIN
        assert checker.resolver.calls == ["MX", "A"]
    finally:
        checker.repository.close()


def test_timeout_during_a_fallback_is_technical_error(tmp_path):
    checker = build_checker(
        tmp_path,
        "a-timeout.db",
        {
            "MX": dns.resolver.NoAnswer(),
            "A": dns.exception.Timeout(timeout=1.0),
            "AAAA": dns.resolver.NoAnswer(),
        },
    )
    try:
        result = checker._lookup_uncached("a-timeout.example")
        assert result.state == DNSState.ERROR
        assert result.detail == "Timeout"
        assert checker.resolver.calls == ["MX", "A"]
    finally:
        checker.repository.close()


def test_generic_dns_exception_during_a_fallback_is_technical_error(tmp_path):
    checker = build_checker(
        tmp_path,
        "a-error.db",
        {
            "MX": dns.resolver.NoAnswer(),
            "A": dns.exception.DNSException("boom"),
            "AAAA": dns.resolver.NoAnswer(),
        },
    )
    try:
        result = checker._lookup_uncached("a-error.example")
        assert result.state == DNSState.ERROR
        assert result.detail == "DNSException"
        assert checker.resolver.calls == ["MX", "A"]
    finally:
        checker.repository.close()
