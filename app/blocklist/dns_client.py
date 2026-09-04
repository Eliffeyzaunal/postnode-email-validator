from copy import deepcopy
from typing import Protocol

import dns.exception
import dns.resolver

from app.blocklist.models import DNSResponse, DNSResponseState


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


class LiveBlocklistDNSClient:
    """DNSBL sorgularını sistem veya açıkça verilen özel çözümleyiciyle yapar."""

    def __init__(
        self,
        timeout_seconds: float = 3.0,
        nameservers: list[str] | None = None,
        resolver: dns.resolver.Resolver | None = None,
    ):
        self.resolver = resolver or dns.resolver.Resolver(configure=True)
        self.resolver.timeout = timeout_seconds
        self.resolver.lifetime = timeout_seconds
        if nameservers:
            self.resolver.nameservers = nameservers

    def resolve(self, query_name: str) -> DNSResponse:
        normalized = query_name.casefold().rstrip(".")
        try:
            answer = self.resolver.resolve(normalized, "A", search=False)
            records = [item.address for item in answer]
        except dns.resolver.NXDOMAIN:
            return DNSResponse(state=DNSResponseState.NXDOMAIN)
        except (dns.resolver.LifetimeTimeout, dns.exception.Timeout) as exc:
            return DNSResponse(state=DNSResponseState.TIMEOUT, detail=str(exc))
        except dns.resolver.NoNameservers as exc:
            return DNSResponse(state=DNSResponseState.SERVFAIL, detail=str(exc))
        except dns.resolver.NoAnswer as exc:
            return DNSResponse(state=DNSResponseState.ERROR, detail=str(exc))
        except dns.exception.DNSException as exc:
            return DNSResponse(state=DNSResponseState.ERROR, detail=str(exc))
        except OSError as exc:
            return DNSResponse(state=DNSResponseState.ERROR, detail=str(exc))

        txt_records: list[str] = []
        try:
            txt_answer = self.resolver.resolve(normalized, "TXT", search=False)
            for item in txt_answer:
                chunks = getattr(item, "strings", ())
                if chunks:
                    txt_records.append(
                        b"".join(chunks).decode("utf-8", errors="replace")
                    )
                else:
                    txt_records.append(str(item).strip('"'))
        except dns.exception.DNSException:
            # Pozitif A cevabı geçerlidir; TXT açıklaması her sağlayıcıda bulunmayabilir.
            pass

        return DNSResponse(
            state=DNSResponseState.OK,
            a_records=records,
            txt_records=txt_records,
        )
