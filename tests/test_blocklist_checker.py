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
