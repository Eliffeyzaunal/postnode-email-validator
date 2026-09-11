import csv
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from scripts.evaluate_task1_live_challenge import (
    DATASET_PATH,
    EXPECTED_SIZE,
    FROZEN_DATASET_SHA256,
    dataset_sha256,
    load_cases,
    resolve_dns_snapshot,
    reference_decision,
)
import scripts.evaluate_task1_live_challenge as live_challenge
from app.models import DNSResult, DNSState, Status
from app.reason_codes import ReasonCode
from scripts.generate_task1_live_challenge import build_cases


ROOT = Path(__file__).resolve().parent.parent


def test_live_challenge_is_frozen_and_has_expected_mix():
    cases = load_cases()
    assert len(cases) == EXPECTED_SIZE == 200
    assert dataset_sha256(DATASET_PATH) == FROZEN_DATASET_SHA256
    assert Counter(case["category"] for case in cases) == {
        "neutral_public_domain": 60,
        "role_account": 40,
        "disposable_domain": 20,
        "provider_typo": 20,
        "invalid_syntax": 25,
        "nonexistent_subdomain": 15,
        "smtputf8": 10,
        "strict_outer_space": 10,
    }


def test_generator_matches_committed_corpus():
    with DATASET_PATH.open(encoding="utf-8", newline="") as stream:
        committed = list(csv.DictReader(stream))
    assert build_cases() == committed


def test_frozen_hash_is_independent_of_checkout_line_endings(tmp_path):
    lf_path = tmp_path / "lf.csv"
    crlf_path = tmp_path / "crlf.csv"
    lf_path.write_bytes(b"header\nvalue\n")
    crlf_path.write_bytes(b"header\r\nvalue\r\n")
    assert dataset_sha256(lf_path) == dataset_sha256(crlf_path)


def test_strict_outer_space_is_decided_without_dns():
    status, evidence = reference_decision(
        "  audit.case@gmail.com  ", "none", DNSState.MX
    )
    assert status == "gecersiz"
    assert evidence == "independent_strict_syntax"


def test_reference_combines_independent_syntax_with_shared_dns_state():
    assert reference_decision("person@gmail.com", "none", DNSState.MX)[0] == "gecerli"
    assert (
        reference_decision("support@gmail.com", "role_account", DNSState.MX)[0]
        == "supheli"
    )
    assert (
        reference_decision("person@missing.example", "none", DNSState.NXDOMAIN)[0]
        == "gecersiz"
    )
    assert reference_decision("person@gmail.com", "none", DNSState.ERROR)[0] is None


def test_live_challenge_requires_explicit_opt_in():
    completed = subprocess.run(
        [sys.executable, "scripts/evaluate_task1_live_challenge.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "--acknowledge-live-dns" in completed.stderr + completed.stdout


def test_live_metric_keeps_raw_policy_difference_and_excludes_dns_unknown(monkeypatch):
    cases = [
        {"case_id": "1", "email": "valid", "category": "neutral", "risk_if_deliverable": "none"},
        {"case_id": "2", "email": "risk", "category": "role_account", "risk_if_deliverable": "role_account"},
        {"case_id": "3", "email": "invalid", "category": "invalid_syntax", "risk_if_deliverable": "none"},
        {"case_id": "4", "email": "trim", "category": "strict_outer_space", "risk_if_deliverable": "none"},
        {"case_id": "5", "email": "unknown", "category": "neutral", "risk_if_deliverable": "none"},
    ]
    reference = {
        "valid": ("gecerli", "independent_live_dns"),
        "risk": ("supheli", "independent_live_dns+role_account"),
        "invalid": ("gecersiz", "independent_strict_syntax"),
        "trim": ("gecersiz", "independent_strict_syntax"),
        "unknown": (None, "independent_dns_unknown"),
    }
    actual = {
        "valid": Status.VALID,
        "risk": Status.SUSPICIOUS,
        "invalid": Status.INVALID,
        "trim": Status.VALID,
        "unknown": Status.SUSPICIOUS,
    }

    monkeypatch.setattr(
        live_challenge,
        "reference_decision",
        lambda email, _risk, _resolver: reference[email],
    )

    class FakeService:
        def validate_one(self, email, persist=False):
            reasons = (
                [ReasonCode.DNS_LOOKUP_ERROR]
                if email == "unknown"
                else [ReasonCode.VALID]
            )
            return "batch", {}, SimpleNamespace(status=actual[email], reason_codes=reasons)

    report = live_challenge.evaluate(cases, {}, FakeService())
    assert report["scored_cases"] == 4
    assert report["unscored_cases"] == 1
    assert report["accuracy"] == 0.75
    assert report["policy_aligned_accuracy"] == 1.0
    assert report["measurement_valid"] is False


def test_dns_snapshot_retries_only_technical_errors():
    class FakeChecker:
        def __init__(self):
            self.calls = Counter()

        def _lookup_uncached(self, domain):
            self.calls[domain] += 1
            if domain == "retry.example" and self.calls[domain] == 1:
                return DNSResult(domain, DNSState.ERROR, "Timeout")
            state = DNSState.NXDOMAIN if domain == "missing.example" else DNSState.MX
            return DNSResult(domain, state, state.value)

    checker = FakeChecker()
    states, report = resolve_dns_snapshot(
        {"retry.example", "missing.example"}, [("resolver-a", checker)], retries=2
    )
    assert states == {
        "missing.example": DNSState.NXDOMAIN,
        "retry.example": DNSState.MX,
    }
    assert checker.calls == Counter({"retry.example": 2, "missing.example": 1})
    assert report["technical_error_count"] == 0
    assert report["state_counts"] == {"mx": 1, "nxdomain": 1}

def test_dns_snapshot_falls_back_to_second_resolver():
    class ErrorChecker:
        def _lookup_uncached(self, domain):
            return DNSResult(domain, DNSState.ERROR, "NoNameservers")

    class SuccessChecker:
        def _lookup_uncached(self, domain):
            return DNSResult(domain, DNSState.MX, "MX kaydi bulundu")

    states, report = resolve_dns_snapshot(
        {"fallback.example"},
        [("1.1.1.1", ErrorChecker()), ("8.8.8.8", SuccessChecker())],
        retries=0,
    )

    assert states["fallback.example"] == DNSState.MX
    assert report["technical_error_count"] == 0
    assert report["resolved_via"]["fallback.example"] == "8.8.8.8"
    assert report["attempts"]["fallback.example"] == 2
