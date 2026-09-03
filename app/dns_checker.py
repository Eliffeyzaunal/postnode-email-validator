from datetime import UTC, datetime, timedelta
from typing import Protocol

import dns.exception
import dns.resolver

from app.models import DNSResult, DNSState
from app.repository import Repository


class DNSLookup(Protocol):
    def lookup(self, domain: str) -> DNSResult: ...


class DNSChecker:
    def __init__(
        self,
        repository: Repository,
        timeout_seconds: float = 2.0,
        ttl_seconds: int = 86_400,
        error_ttl_seconds: int = 300,
    ):
        self.repository = repository
        self.ttl_seconds = ttl_seconds
        self.error_ttl_seconds = error_ttl_seconds
        self.resolver = dns.resolver.Resolver(configure=True)
        self.resolver.timeout = timeout_seconds
        self.resolver.lifetime = timeout_seconds

    def lookup(self, domain: str) -> DNSResult:
        cached = self.repository.get_cached_dns(domain)
        if cached:
            return cached

        result = self._lookup_uncached(domain)
        checked_at = datetime.now(UTC)
        ttl = self.error_ttl_seconds if result.state == DNSState.ERROR else self.ttl_seconds
        self.repository.put_dns(result, checked_at, checked_at + timedelta(seconds=ttl))
        return result

    def _lookup_uncached(self, domain: str) -> DNSResult:
        try:
            answers = self.resolver.resolve(domain, "MX")
            if answers:
                return DNSResult(domain, DNSState.MX, "MX kaydı bulundu")
        except dns.resolver.NXDOMAIN:
            return DNSResult(domain, DNSState.NXDOMAIN, "Alan adı bulunamadı")
        except dns.resolver.NoAnswer:
            pass
        except (dns.exception.Timeout, dns.resolver.NoNameservers) as exc:
            return DNSResult(domain, DNSState.ERROR, type(exc).__name__)
        except dns.exception.DNSException as exc:
            return DNSResult(domain, DNSState.ERROR, type(exc).__name__)

        for record_type in ("A", "AAAA"):
            try:
                answers = self.resolver.resolve(domain, record_type)
                if answers:
                    return DNSResult(domain, DNSState.A_FALLBACK, f"{record_type} kaydı bulundu")
            except dns.resolver.NXDOMAIN:
                return DNSResult(domain, DNSState.NXDOMAIN, "Alan adı bulunamadı")
            except dns.resolver.NoAnswer:
                continue
            except (dns.exception.Timeout, dns.resolver.NoNameservers) as exc:
                return DNSResult(domain, DNSState.ERROR, type(exc).__name__)
            except dns.exception.DNSException as exc:
                return DNSResult(domain, DNSState.ERROR, type(exc).__name__)
        return DNSResult(domain, DNSState.NO_MAIL_HOST, "MX, A ve AAAA kaydı yok")


class StaticDNSChecker:
    """Test ve belirleyici değerlendirme koşuları için ağsız DNS sağlayıcısı."""

    def __init__(self, states: dict[str, DNSState], default: DNSState = DNSState.MX):
        self.states = states
        self.default = default
        self.calls: dict[str, int] = {}

    def lookup(self, domain: str) -> DNSResult:
        self.calls[domain] = self.calls.get(domain, 0) + 1
        return DNSResult(domain, self.states.get(domain, self.default), "static")

