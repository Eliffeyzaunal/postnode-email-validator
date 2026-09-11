import dns.exception
import dns.resolver

from app.blocklist.dns_client import LiveBlocklistDNSClient
from app.blocklist.models import DNSResponseState


class ARecord:
    def __init__(self, address: str):
        self.address = address


class TXTRecord:
    def __init__(self, value: str):
        self.strings = (value.encode(),)


class ResolverStub:
    def __init__(self, a_response=None, txt_response=None):
        self.a_response = a_response
        self.txt_response = txt_response or []
        self.timeout = None
        self.lifetime = None

    def resolve(self, _query, record_type, search=False):
        assert search is False
        response = self.a_response if record_type == "A" else self.txt_response
        if isinstance(response, Exception):
            raise response
        return response


def test_live_dns_reads_a_and_txt_records():
    resolver = ResolverStub(
        [ARecord("127.0.0.2")],
        [TXTRecord("test listing reason")],
    )
    response = LiveBlocklistDNSClient(resolver=resolver).resolve(
        "2.0.0.127.zen.spamhaus.org"
    )

    assert response.state == DNSResponseState.OK
    assert response.a_records == ["127.0.0.2"]
    assert response.txt_records == ["test listing reason"]


def test_live_dns_nxdomain_is_clean_answer():
    resolver = ResolverStub(dns.resolver.NXDOMAIN())
    response = LiveBlocklistDNSClient(resolver=resolver).resolve("clean.example")

    assert response.state == DNSResponseState.NXDOMAIN


def test_live_dns_timeout_is_not_clean_answer():
    resolver = ResolverStub(dns.exception.Timeout("resolver timed out"))
    response = LiveBlocklistDNSClient(resolver=resolver).resolve("error.example")

    assert response.state == DNSResponseState.TIMEOUT
    assert "timed out" in response.detail


def test_live_dns_no_answer_is_query_error_state():
    resolver = ResolverStub(dns.resolver.NoAnswer())
    response = LiveBlocklistDNSClient(resolver=resolver).resolve("empty.example")

    assert response.state == DNSResponseState.ERROR

class TXTRecordWithoutStrings:
    def __str__(self):
        return '"fallback text"'


def test_live_dns_applies_explicit_nameservers():
    resolver = ResolverStub([])
    client = LiveBlocklistDNSClient(
        timeout_seconds=7,
        nameservers=["1.1.1.1", "8.8.8.8"],
        resolver=resolver,
    )

    assert resolver.timeout == 7
    assert resolver.lifetime == 7
    assert resolver.nameservers == ["1.1.1.1", "8.8.8.8"]
    assert client.resolver is resolver


def test_live_dns_no_nameservers_is_servfail():
    resolver = ResolverStub(dns.resolver.NoNameservers())
    response = LiveBlocklistDNSClient(resolver=resolver).resolve("servfail.example")

    assert response.state == DNSResponseState.SERVFAIL


def test_live_dns_generic_dns_exception_is_error():
    resolver = ResolverStub(dns.exception.DNSException("dns failed"))
    response = LiveBlocklistDNSClient(resolver=resolver).resolve("dns-error.example")

    assert response.state == DNSResponseState.ERROR
    assert "dns failed" in response.detail


def test_live_dns_oserror_is_error():
    resolver = ResolverStub(OSError("network unavailable"))
    response = LiveBlocklistDNSClient(resolver=resolver).resolve("os-error.example")

    assert response.state == DNSResponseState.ERROR
    assert "network unavailable" in response.detail


def test_live_dns_txt_falls_back_to_string_representation():
    resolver = ResolverStub(
        [ARecord("127.0.0.2")],
        [TXTRecordWithoutStrings()],
    )
    response = LiveBlocklistDNSClient(resolver=resolver).resolve("txt.example")

    assert response.state == DNSResponseState.OK
    assert response.txt_records == ["fallback text"]


def test_live_dns_keeps_positive_a_when_txt_lookup_fails():
    resolver = ResolverStub(
        [ARecord("127.0.0.2")],
        dns.resolver.NoAnswer(),
    )
    response = LiveBlocklistDNSClient(resolver=resolver).resolve("txt-missing.example")

    assert response.state == DNSResponseState.OK
    assert response.a_records == ["127.0.0.2"]
    assert response.txt_records == []
