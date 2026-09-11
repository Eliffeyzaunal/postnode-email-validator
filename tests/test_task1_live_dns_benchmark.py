from dataclasses import replace

from app.models import DNSResult, DNSState
from scripts.benchmark_live_dns import load_domains, markdown, run_benchmark


class CacheFixture:
    def __init__(self):
        self.cache = {}

    def lookup(self, domain):
        if domain in self.cache:
            return replace(self.cache[domain], from_cache=True)
        result = DNSResult(domain, DNSState.MX, "fixture")
        self.cache[domain] = result
        return result


def test_live_dns_benchmark_reporting_is_separate_and_cache_checked(tmp_path):
    path = tmp_path / "domains.txt"
    path.write_text("gmail.com\nexample.com\n", encoding="utf-8")
    report = run_benchmark(CacheFixture(), load_domains(path))
    report.update(
        measured_at="2026-09-10T00:00:00+00:00",
        platform="test",
        python_version="3.12",
        resolver_nameservers=["192.0.2.53"],
    )
    assert report["domain_count"] == 2
    assert report["warm_cache_hits"] == 2
    assert report["measurement_valid"] is True
    assert "karşılaştırması yapılamaz" in markdown(report)
