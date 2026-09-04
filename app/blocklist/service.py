from collections import Counter
from pathlib import Path
import uuid

from app.blocklist.checker import BlocklistChecker
from app.blocklist.config_loader import (
    load_assets,
    load_fake_responses,
    load_providers,
)
from app.blocklist.dns_client import (
    BlocklistDNSClient,
    FakeBlocklistDNSClient,
    LiveBlocklistDNSClient,
)
from app.blocklist.models import (
    BlocklistCheckRequest,
    BlocklistRunResponse,
    BlocklistSummary,
    CheckStatus,
    MonitoredAsset,
    ProviderDefinition,
)
from app.blocklist.repository import BlocklistRepository
from app.config import Settings


class BlocklistMonitorService:
    def __init__(
        self,
        settings: Settings,
        repository: BlocklistRepository | None = None,
        dns_client: BlocklistDNSClient | None = None,
    ):
        self.settings = settings
        self.repository = repository or BlocklistRepository(settings.database_url)
        self.providers = load_providers(settings.blocklist_providers_path)
        if dns_client is None:
            dns_client = self._build_dns_client(settings)
        self.dns_client = dns_client
        self.checker = BlocklistChecker(dns_client)

    @staticmethod
    def _build_dns_client(settings: Settings) -> BlocklistDNSClient:
        if settings.blocklist_dns_mode == "live":
            nameservers = (
                [item.strip() for item in settings.blocklist_nameservers.split(",") if item.strip()]
                if settings.blocklist_nameservers
                else None
            )
            return LiveBlocklistDNSClient(
                timeout_seconds=settings.blocklist_dns_timeout_seconds,
                nameservers=nameservers,
            )
        default, responses = load_fake_responses(settings.blocklist_fake_dns_path)
        return FakeBlocklistDNSClient(default, responses)

    def run_once(
        self,
        request: BlocklistCheckRequest | None = None,
        source_path: Path | None = None,
    ) -> BlocklistRunResponse:
        assets = (
            request.assets
            if request is not None and request.assets is not None
            else load_assets(source_path or self.settings.blocklist_assets_path)
        )
        if not assets:
            raise ValueError("En az bir izlenecek varlık gereklidir.")
        self._ensure_unique_assets(assets)

        results = []
        for asset in assets:
            for provider in self.providers:
                if asset.type in provider.asset_types:
                    results.append(self.checker.check(asset, provider))

        run_id = str(uuid.uuid4())
        notifications = self.repository.save_run(
            run_id,
            (source_path or self.settings.blocklist_assets_path).name
            if request is None or request.assets is None
            else None,
            results,
        )
        counts = Counter(item.status for item in results)
        summary = BlocklistSummary(
            total=len(results),
            listed=counts[CheckStatus.LISTED],
            not_listed=counts[CheckStatus.NOT_LISTED],
            query_error=counts[CheckStatus.QUERY_ERROR],
            unavailable=counts[CheckStatus.UNAVAILABLE],
        )
        return BlocklistRunResponse(
            run_id=run_id,
            source_filename=(
                (source_path or self.settings.blocklist_assets_path).name
                if request is None or request.assets is None
                else None
            ),
            summary=summary,
            results=results,
            notifications=notifications,
        )

    @staticmethod
    def _ensure_unique_assets(assets: list[MonitoredAsset]) -> None:
        identifiers = [item.id for item in assets]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Varlık kimlikleri benzersiz olmalıdır.")

    def provider_status(self) -> list[dict]:
        return [
            {
                "id": provider.id,
                "name": provider.name,
                "asset_types": [item.value for item in provider.asset_types],
                "availability": provider.availability.value,
                "severity": provider.severity,
                "unavailable_reason": provider.unavailable_reason,
                "source_url": provider.source_url,
            }
            for provider in self.providers
        ]
