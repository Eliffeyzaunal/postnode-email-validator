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
