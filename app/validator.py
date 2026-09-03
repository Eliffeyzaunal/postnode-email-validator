import json
import re
import time
import uuid
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.config import Settings
from app.dns_checker import DNSChecker, DNSLookup
from app.models import DNSState, InternalResult, Status
from app.reason_codes import ReasonCode
from app.repository import Repository
from app.syntax import validate_syntax


SEQUENCE_PATTERN = re.compile(r"^(.*?)(\d+)$")


def _read_lines(path: Path) -> set[str]:
    return {
        line.strip().casefold()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


class EmailValidatorService:
    def __init__(
        self,
        settings: Settings,
        repository: Repository | None = None,
        dns_checker: DNSLookup | None = None,
    ):
        self.settings = settings
        self.repository = repository or Repository(settings.database_url)
        self.dns_checker = dns_checker or DNSChecker(
            self.repository,
            settings.dns_timeout_seconds,
            settings.dns_cache_ttl_seconds,
            settings.dns_error_cache_ttl_seconds,
        )
        self.disposable_domains = _read_lines(settings.disposable_domains_path)
        self.role_accounts = _read_lines(settings.role_accounts_path)
        self.domain_typos: dict[str, str] = json.loads(
            settings.domain_typos_path.read_text(encoding="utf-8")
        )

    def validate_many(
        self, emails: list[str], filename: str | None = None, persist: bool = True
    ) -> tuple[str, dict, list[InternalResult]]:
        if not emails:
            raise ValueError("En az bir adres gereklidir.")
        if len(emails) > self.settings.max_batch_size:
            raise ValueError(f"En fazla {self.settings.max_batch_size} adres işlenebilir.")

        started = time.perf_counter()
        results: list[InternalResult] = []
        unique_domains: set[str] = set()

        for row_number, raw in enumerate(emails, start=1):
            syntax = validate_syntax(raw)
            if not syntax.valid:
                results.append(
                    InternalResult(
                        row_number, raw, syntax.normalized, syntax.domain, syntax.local_part,
                        Status.INVALID, list(syntax.reason_codes)
                    )
                )
                continue
            unique_domains.add(syntax.domain or "")
            results.append(
                InternalResult(
                    row_number, raw, syntax.normalized, syntax.domain, syntax.local_part,
                    Status.VALID, []
                )
            )

        dns_results = self._lookup_domains(unique_domains)
        self._apply_address_rules(results, dns_results)
        self._apply_list_rules(results)
        self._finalize_statuses(results)

        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        summary = self._summarize(results, duration_ms)
        batch_id = str(uuid.uuid4())
        if persist:
            self.repository.save_batch(batch_id, filename, summary, results)
        return batch_id, summary, results

    def validate_one(self, email: str, persist: bool = True) -> tuple[str, dict, InternalResult]:
        batch_id, summary, results = self.validate_many([email], persist=persist)
        return batch_id, summary, results[0]

    def _lookup_domains(self, domains: set[str]) -> dict[str, object]:
        ordered = sorted(domain for domain in domains if domain)
        if not ordered:
            return {}
        with ThreadPoolExecutor(max_workers=min(self.settings.max_dns_workers, len(ordered))) as pool:
            resolved = list(pool.map(self.dns_checker.lookup, ordered))
        return {item.domain: item for item in resolved}

    def _apply_address_rules(self, results: list[InternalResult], dns_results: dict[str, object]) -> None:
        for item in results:
            if item.status == Status.INVALID or not item.domain or not item.local_part:
                continue
            dns_result = dns_results[item.domain]
            if dns_result.state == DNSState.NXDOMAIN:
                item.reason_codes.append(ReasonCode.DOMAIN_NXDOMAIN)
            elif dns_result.state == DNSState.NO_MAIL_HOST:
                item.reason_codes.append(ReasonCode.DOMAIN_NO_MAIL_HOST)
            elif dns_result.state == DNSState.A_FALLBACK:
                item.reason_codes.append(ReasonCode.DOMAIN_A_FALLBACK)
            elif dns_result.state == DNSState.ERROR:
                item.reason_codes.append(ReasonCode.DNS_LOOKUP_ERROR)

            if item.domain in self.disposable_domains:
                item.reason_codes.append(ReasonCode.DISPOSABLE_DOMAIN)
            if item.local_part.casefold() in self.role_accounts:
                item.reason_codes.append(ReasonCode.ROLE_ACCOUNT)
            if item.domain in self.domain_typos:
                replacement = self.domain_typos[item.domain]
                item.reason_codes.append(ReasonCode.DOMAIN_TYPO)
                item.suggestion = f"{item.local_part}@{replacement}"

    def _apply_list_rules(self, results: list[InternalResult]) -> None:
        seen: set[str] = set()
        valid_items = [item for item in results if item.normalized and item.domain]
        for item in valid_items:
            key = (item.normalized or "").casefold()
            if key in seen:
                item.reason_codes.append(ReasonCode.DUPLICATE_ADDRESS)
            seen.add(key)

        if len(valid_items) >= self.settings.domain_concentration_min_list_size:
            domain_counts = Counter(item.domain for item in valid_items)
            concentrated = {
                domain for domain, count in domain_counts.items()
                if count / len(valid_items) >= self.settings.domain_concentration_threshold
            }
            for item in valid_items:
                if item.domain in concentrated:
                    item.reason_codes.append(ReasonCode.DOMAIN_CONCENTRATION)

        groups: dict[tuple[str, str], list[tuple[int, InternalResult]]] = defaultdict(list)
        for item in valid_items:
            match = SEQUENCE_PATTERN.match(item.local_part or "")
            if match:
                groups[(item.domain or "", match.group(1).casefold())].append((int(match.group(2)), item))
        for entries in groups.values():
            numbers = sorted({number for number, _ in entries})
            if len(numbers) < 5:
                continue
            span = numbers[-1] - numbers[0] + 1
            if span > 0 and len(numbers) / span >= 0.80:
                for _, item in entries:
                    item.reason_codes.append(ReasonCode.GENERATED_SEQUENCE)

    @staticmethod
    def _finalize_statuses(results: list[InternalResult]) -> None:
        invalid_codes = {
            ReasonCode.EMPTY_EMAIL,
            ReasonCode.INVALID_SYNTAX,
            ReasonCode.EMAIL_TOO_LONG,
            ReasonCode.LOCAL_PART_TOO_LONG,
            ReasonCode.INVALID_LOCAL_PART,
            ReasonCode.INVALID_DOMAIN,
            ReasonCode.DOMAIN_NXDOMAIN,
            ReasonCode.DOMAIN_NO_MAIL_HOST,
        }
        for item in results:
            item.reason_codes = list(dict.fromkeys(item.reason_codes))
            if any(code in invalid_codes for code in item.reason_codes):
                item.status = Status.INVALID
            elif item.reason_codes:
                item.status = Status.SUSPICIOUS
            else:
                item.status = Status.VALID
                item.reason_codes = [ReasonCode.VALID]

    @staticmethod
    def _summarize(results: list[InternalResult], duration_ms: float) -> dict:
        statuses = Counter(item.status for item in results)
        domains = Counter(item.domain for item in results if item.domain)
        total = len(results)
        invalid = statuses[Status.INVALID]
        suspicious = statuses[Status.SUSPICIOUS]
        estimated = round((invalid + suspicious * 0.25) / total, 4) if total else 0.0
        return {
            "total": total,
            "valid": statuses[Status.VALID],
            "suspicious": suspicious,
            "invalid": invalid,
            "estimated_bounce_rate": estimated,
            "top_domains": dict(domains.most_common(10)),
            "duration_ms": duration_ms,
        }
