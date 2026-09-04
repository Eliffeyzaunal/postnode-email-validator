import json
from pathlib import Path

from app.blocklist.models import DNSResponse, MonitoredAsset, ProviderDefinition


def load_assets(path: Path) -> list[MonitoredAsset]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assets = [MonitoredAsset.model_validate(item) for item in payload.get("assets", [])]
    if not assets:
        raise ValueError("Yapılandırmada en az bir izlenecek varlık bulunmalıdır.")
    ids = [item.id for item in assets]
    if len(ids) != len(set(ids)):
        raise ValueError("İzlenen varlık kimlikleri benzersiz olmalıdır.")
    return assets


def load_providers(path: Path) -> list[ProviderDefinition]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    providers = [
        ProviderDefinition.model_validate(item) for item in payload.get("providers", [])
    ]
    if not providers:
        raise ValueError("En az bir blocklist sağlayıcısı tanımlanmalıdır.")
    return providers


def load_fake_responses(path: Path) -> tuple[DNSResponse, dict[str, DNSResponse]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    default = DNSResponse.model_validate(payload["default"])
    responses = {
        query.casefold().rstrip("."): DNSResponse.model_validate(response)
        for query, response in payload.get("responses", {}).items()
    }
    return default, responses

