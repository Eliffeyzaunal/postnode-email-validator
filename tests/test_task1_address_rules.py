import json

import pytest

from app.address_rules import (
    bounded_levenshtein,
    is_disposable_domain,
    is_role_account,
    suggest_domain_typo,
)
from app.models import Status
from app.reason_codes import ReasonCode
from scripts.update_disposable_domains import normalize_domains, refresh


def test_disposable_matches_exact_and_parent_domain():
    blocked = {"mailinator.com", "temporary.co.uk"}
    assert is_disposable_domain("mailinator.com", blocked)
    assert is_disposable_domain("inbox.mailinator.com", blocked)
    assert is_disposable_domain("mx.temporary.co.uk", blocked)
    assert not is_disposable_domain("mailinator.com.example", blocked)


@pytest.mark.parametrize("local", ["info", "INFO+ticket", "sales-eu", "support.tr", "no-reply+case"])
def test_role_variants_are_conservative(local):
    roles = {"info", "sales", "support", "no-reply"}
    suffixes = {"ticket", "eu", "tr", "case"}
    assert is_role_account(local, roles, suffixes)


@pytest.mark.parametrize("local", ["information", "elif.support", "personal+info", "salesforce"])
def test_personal_mailboxes_are_not_role_variants(local):
    assert not is_role_account(
        local, {"info", "sales", "support"}, {"ticket", "eu", "tr"}
    )


def test_fuzzy_typo_is_unique_same_tld_and_never_targets_known_domain():
    popular = {"gmail.com", "mail.com", "hotmail.com", "outlook.com"}
    assert suggest_domain_typo("gmaik.com", {}, popular) == "gmail.com"
    assert suggest_domain_typo("gmail.com", {}, popular) is None
    assert suggest_domain_typo("gmail.co", {}, popular) is None
    assert suggest_domain_typo("gmaik.com.example", {}, popular) is None
    assert bounded_levenshtein("gmail", "gmaik", 1) == 1


def test_fuzzy_typo_stays_suspicious(service, dns_checker):
    dns_checker.states["gmaik.com"] = dns_checker.states["gmail.com"]
    _, _, result = service.validate_one("person@gmaik.com", persist=False)
    assert result.status == Status.SUSPICIOUS
    assert ReasonCode.DOMAIN_TYPO in result.reason_codes
    assert result.suggestion == "person@gmail.com"


def test_snapshot_update_normalizes_and_rejects_truncated_input(tmp_path):
    assert normalize_domains("B.example\na.example\na.example\n") == ["a.example", "b.example"]
    with pytest.raises(ValueError, match="suspiciously small"):
        refresh("one.example\n", tmp_path / "domains.txt", tmp_path / "meta.json", "fixture", "abc")
    metadata = refresh(
        "B.example\na.example\n",
        tmp_path / "domains.txt",
        tmp_path / "meta.json",
        "fixture",
        "abc",
        minimum_count=2,
    )
    assert metadata["domain_count"] == 2
    assert json.loads((tmp_path / "meta.json").read_text())["source_commit"] == "abc"
