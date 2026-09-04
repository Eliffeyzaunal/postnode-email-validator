from __future__ import annotations

import ipaddress
from datetime import UTC, datetime
from urllib.parse import quote

from app.blocklist.dns_client import BlocklistDNSClient
from app.blocklist.models import (
    Availability,
    BlocklistCheckResult,
    CheckStatus,
    DNSResponse,
    DNSResponseState,
    MonitoredAsset,
    ProviderDefinition,
)


class BlocklistChecker:
    def __init__(self, dns_client: BlocklistDNSClient):
        self.dns_client = dns_client

    def check(
        self, asset: MonitoredAsset, provider: ProviderDefinition
    ) -> BlocklistCheckResult:
        checked_at = datetime.now(UTC)
        removal_url = (
            provider.removal_url.format(asset=quote(asset.value, safe=".:"))
            if provider.removal_url
            else None
        )
        if provider.availability == Availability.UNAVAILABLE:
            return BlocklistCheckResult(
                asset_id=asset.id,
                asset_type=asset.type,
                asset_value=asset.value,
                provider_id=provider.id,
                provider_name=provider.name,
                status=CheckStatus.UNAVAILABLE,
                severity=provider.severity,
                reasons=[provider.unavailable_reason or "Sağlayıcı kullanılamıyor."],
                removal_url=removal_url,
                checked_at=checked_at,
                detail=provider.unavailable_reason,
            )

        query_name = self.build_query_name(asset, provider)
        response = self.dns_client.resolve(query_name)
        status, codes, reasons, detail = self._interpret(provider, response)
        return BlocklistCheckResult(
            asset_id=asset.id,
            asset_type=asset.type,
            asset_value=asset.value,
            provider_id=provider.id,
            provider_name=provider.name,
            status=status,
            severity=provider.severity,
            query_name=query_name,
            return_codes=codes,
            reasons=reasons,
            removal_url=removal_url,
            checked_at=checked_at,
            detail=detail,
        )

    @staticmethod
    def build_query_name(
        asset: MonitoredAsset, provider: ProviderDefinition
    ) -> str:
        if asset.type not in provider.asset_types:
            raise ValueError(f"{provider.id}, {asset.type.value} türünü desteklemiyor.")
        if not provider.zone or not provider.query_mode:
            raise ValueError(f"{provider.id} için DNS sorgu bilgisi eksik.")
        if provider.query_mode == "domain":
            query_value = asset.value.casefold().rstrip(".")
        else:
            address = ipaddress.ip_address(asset.value)
            if address.version == 4:
                query_value = ".".join(reversed(address.exploded.split(".")))
            else:
                query_value = ".".join(reversed(address.exploded.replace(":", "")))
        return f"{query_value}.{provider.zone}".casefold()

    @staticmethod
    def _interpret(
        provider: ProviderDefinition, response: DNSResponse
    ) -> tuple[CheckStatus, list[str], list[str], str | None]:
        if response.state == DNSResponseState.NXDOMAIN:
            return CheckStatus.NOT_LISTED, [], [], response.detail
        if response.state != DNSResponseState.OK:
            detail = response.detail or f"DNS sorgu durumu: {response.state.value}"
            return CheckStatus.QUERY_ERROR, [], [], detail
        if not response.a_records:
            return CheckStatus.NOT_LISTED, [], response.txt_records, response.detail

        error_labels = [
            provider.error_codes[record]
            for record in response.a_records
            if record in provider.error_codes
        ]
        if error_labels:
            return (
                CheckStatus.QUERY_ERROR,
                error_labels,
                response.txt_records,
                ", ".join(error_labels),
            )

        invalid_records = []
        for record in response.a_records:
            try:
                if not ipaddress.ip_address(record).is_loopback:
                    invalid_records.append(record)
            except ValueError:
                invalid_records.append(record)
        if invalid_records:
            detail = f"Beklenmeyen DNSBL cevabı: {', '.join(invalid_records)}"
            return CheckStatus.QUERY_ERROR, [], response.txt_records, detail

        decoded: list[str] = []
        if provider.bitmask_codes:
            for record in response.a_records:
                last_octet = int(record.rsplit(".", 1)[1])
                for bit_text, label in provider.bitmask_codes.items():
                    if last_octet & int(bit_text):
                        decoded.append(label)
        else:
            decoded = [
                provider.return_codes.get(record, f"UNKNOWN_CODE:{record}")
                for record in response.a_records
            ]
        return (
            CheckStatus.LISTED,
            list(dict.fromkeys(decoded)),
            response.txt_records,
            response.detail,
        )
