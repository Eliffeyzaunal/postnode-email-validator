from copy import deepcopy
from typing import Protocol

from app.blocklist.models import DNSResponse


class BlocklistDNSClient(Protocol):
    def resolve(self, query_name: str) -> DNSResponse: ...


class FakeBlocklistDNSClient:
    """Ağ bağlantısı kurmadan belirleyici DNSBL cevapları döndürür."""

    def __init__(self, default: DNSResponse, responses: dict[str, DNSResponse]):
        self.default = default
        self.responses = {
            query.casefold().rstrip("."): response for query, response in responses.items()
        }
        self.calls: list[str] = []

    def resolve(self, query_name: str) -> DNSResponse:
        normalized = query_name.casefold().rstrip(".")
        self.calls.append(normalized)
        return deepcopy(self.responses.get(normalized, self.default))

    def set_response(self, query_name: str, response: DNSResponse) -> None:
        self.responses[query_name.casefold().rstrip(".")] = response

