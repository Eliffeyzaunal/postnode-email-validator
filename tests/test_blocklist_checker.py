from app.blocklist.checker import BlocklistChecker
from app.blocklist.dns_client import FakeBlocklistDNSClient
from app.blocklist.models import (
    AssetType,
    Availability,
    CheckStatus,
    DNSResponse,
    DNSResponseState,
    MonitoredAsset,
    ProviderDefinition,
)


def _client(responses=None):
    return FakeBlocklistDNSClient(
        DNSResponse(state=DNSResponseState.NXDOMAIN),
        responses or {},
    )


def test_ipv4_query_reverses_octets():
    provider = ProviderDefinition(
        id="sample",
        name="Sample",
        asset_types=[AssetType.IP],
        availability=Availability.AVAILABLE,
        zone="dnsbl.example",
        query_mode="reverse_ip",
        source_url="https://example.com",
    )
    asset = MonitoredAsset(id="mail-ip", type="ip", value="192.0.2.45")

    assert BlocklistChecker.build_query_name(asset, provider) == "45.2.0.192.dnsbl.example"


def test_surbl_bitmask_is_decoded():
    provider = ProviderDefinition(
        id="surbl",
        name="SURBL Multi",
        asset_types=[AssetType.DOMAIN],
        availability=Availability.AVAILABLE,
        zone="multi.surbl.org",
        query_mode="domain",
        bitmask_codes={"16": "MALWARE", "64": "ABUSE"},
        source_url="https://www.surbl.org",
    )
    query = "test.surbl.org.multi.surbl.org"
    client = _client({query: DNSResponse(state="ok", a_records=["127.0.0.80"])})
    result = BlocklistChecker(client).check(
        MonitoredAsset(id="domain", type="domain", value="test.surbl.org"),
        provider,
    )

    assert result.status == CheckStatus.LISTED
    assert result.return_codes == ["MALWARE", "ABUSE"]


def test_spamhaus_access_code_is_query_error_not_listing():
    provider = ProviderDefinition(
        id="spamhaus",
        name="Spamhaus",
        asset_types=[AssetType.IP],
        availability=Availability.AVAILABLE,
        zone="zen.spamhaus.org",
        query_mode="reverse_ip",
        error_codes={"127.255.255.254": "PUBLIC_RESOLVER_BLOCKED"},
        source_url="https://www.spamhaus.org",
    )
    query = "2.0.0.127.zen.spamhaus.org"
    client = _client({query: DNSResponse(state="ok", a_records=["127.255.255.254"])})
    result = BlocklistChecker(client).check(
        MonitoredAsset(id="ip", type="ip", value="127.0.0.2"),
        provider,
    )

    assert result.status == CheckStatus.QUERY_ERROR
    assert result.return_codes == ["PUBLIC_RESOLVER_BLOCKED"]


def test_unavailable_provider_does_not_make_dns_query():
    provider = ProviderDefinition(
        id="sorbs",
        name="SORBS",
        asset_types=[AssetType.IP],
        availability=Availability.UNAVAILABLE,
        unavailable_reason="Hizmet sonlandırıldı.",
        source_url="https://example.com/sorbs-eol",
    )
    client = _client()
    result = BlocklistChecker(client).check(
        MonitoredAsset(id="ip", type="ip", value="127.0.0.2"),
        provider,
    )

    assert result.status == CheckStatus.UNAVAILABLE
    assert client.calls == []

def test_ipv6_query_reverses_nibbles():
    import ipaddress

    provider = ProviderDefinition(
        id="ipv6",
        name="IPv6 DNSBL",
        asset_types=[AssetType.IP],
        availability=Availability.AVAILABLE,
        zone="dnsbl.example",
        query_mode="reverse_ip",
        source_url="https://example.com",
    )
    asset = MonitoredAsset(id="ipv6-mail", type="ip", value="2001:db8::1")
    exploded = ipaddress.ip_address(asset.value).exploded.replace(":", "")
    expected = ".".join(reversed(exploded)) + ".dnsbl.example"

    assert BlocklistChecker.build_query_name(asset, provider) == expected


def test_provider_rejects_unsupported_asset_type():
    import pytest

    provider = ProviderDefinition(
        id="domain-only",
        name="Domain only",
        asset_types=[AssetType.DOMAIN],
        availability=Availability.AVAILABLE,
        zone="dnsbl.example",
        query_mode="domain",
        source_url="https://example.com",
    )
    asset = MonitoredAsset(id="ip", type="ip", value="127.0.0.2")

    with pytest.raises(ValueError, match="desteklemiyor"):
        BlocklistChecker.build_query_name(asset, provider)


def test_non_ok_dns_state_without_detail_is_query_error():
    provider = ProviderDefinition(
        id="sample",
        name="Sample",
        asset_types=[AssetType.DOMAIN],
        availability=Availability.AVAILABLE,
        zone="dnsbl.example",
        query_mode="domain",
        source_url="https://example.com",
    )

    status, codes, reasons, detail = BlocklistChecker._interpret(
        provider,
        DNSResponse(state=DNSResponseState.TIMEOUT),
    )

    assert status == CheckStatus.QUERY_ERROR
    assert codes == []
    assert reasons == []
    assert detail == "DNS sorgu durumu: timeout"


def test_ok_without_a_records_is_not_listed_and_preserves_txt():
    provider = ProviderDefinition(
        id="sample",
        name="Sample",
        asset_types=[AssetType.DOMAIN],
        availability=Availability.AVAILABLE,
        zone="dnsbl.example",
        query_mode="domain",
        source_url="https://example.com",
    )

    status, codes, reasons, detail = BlocklistChecker._interpret(
        provider,
        DNSResponse(
            state=DNSResponseState.OK,
            a_records=[],
            txt_records=["clean explanation"],
            detail="no A answer",
        ),
    )

    assert status == CheckStatus.NOT_LISTED
    assert codes == []
    assert reasons == ["clean explanation"]
    assert detail == "no A answer"


def test_unexpected_non_loopback_dnsbl_answer_is_query_error():
    provider = ProviderDefinition(
        id="sample",
        name="Sample",
        asset_types=[AssetType.DOMAIN],
        availability=Availability.AVAILABLE,
        zone="dnsbl.example",
        query_mode="domain",
        source_url="https://example.com",
    )

    status, codes, reasons, detail = BlocklistChecker._interpret(
        provider,
        DNSResponse(state=DNSResponseState.OK, a_records=["8.8.8.8"]),
    )

    assert status == CheckStatus.QUERY_ERROR
    assert codes == []
    assert "8.8.8.8" in detail


def test_malformed_dnsbl_answer_is_query_error():
    provider = ProviderDefinition(
        id="sample",
        name="Sample",
        asset_types=[AssetType.DOMAIN],
        availability=Availability.AVAILABLE,
        zone="dnsbl.example",
        query_mode="domain",
        source_url="https://example.com",
    )

    status, codes, reasons, detail = BlocklistChecker._interpret(
        provider,
        DNSResponse(state=DNSResponseState.OK, a_records=["not-an-ip"]),
    )

    assert status == CheckStatus.QUERY_ERROR
    assert codes == []
    assert "not-an-ip" in detail


def test_unknown_loopback_return_code_is_preserved_as_unknown_code():
    provider = ProviderDefinition(
        id="sample",
        name="Sample",
        asset_types=[AssetType.DOMAIN],
        availability=Availability.AVAILABLE,
        zone="dnsbl.example",
        query_mode="domain",
        return_codes={"127.0.0.2": "KNOWN"},
        source_url="https://example.com",
    )

    status, codes, _, _ = BlocklistChecker._interpret(
        provider,
        DNSResponse(state=DNSResponseState.OK, a_records=["127.0.0.99"]),
    )

    assert status == CheckStatus.LISTED
    assert codes == ["UNKNOWN_CODE:127.0.0.99"]
