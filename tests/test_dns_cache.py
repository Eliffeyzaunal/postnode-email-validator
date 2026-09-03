from unittest.mock import Mock

from app.dns_checker import DNSChecker
from app.models import DNSResult, DNSState
from app.repository import Repository


def test_dns_cache_prevents_second_network_lookup(tmp_path):
    repository = Repository(f"sqlite:///{(tmp_path / 'cache.db').as_posix()}")
    checker = DNSChecker(repository, ttl_seconds=3600)
    checker._lookup_uncached = Mock(return_value=DNSResult("gmail.com", DNSState.MX, "test"))

    first = checker.lookup("gmail.com")
    second = checker.lookup("gmail.com")

    assert first.state == DNSState.MX
    assert second.from_cache is True
    checker._lookup_uncached.assert_called_once_with("gmail.com")
    repository.close()
