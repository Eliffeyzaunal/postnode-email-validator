import json
from pathlib import Path

from app.reason_codes import ReasonCode
from app.syntax import validate_syntax
from scripts.evaluate_task1_holdout import DATASET_PATH, FROZEN_DATASET_SHA256
from scripts.evaluate_task1_holdout import evaluate as evaluate_holdout
from scripts.evaluate_task1_holdout import load_holdout
from scripts.evaluate_task1_syntax_reference import evaluate as evaluate_reference


ROOT = Path(__file__).resolve().parent.parent


def test_frozen_holdout_is_balanced_disjoint_and_reproducible():
    cases = load_holdout()
    report = evaluate_holdout(cases)

    assert len(cases) == 300
    assert report["class_balance"] == {"gecerli": 100, "supheli": 100, "gecersiz": 100}
    assert report["acceptance_dataset_overlap"] == 0
    assert report["accuracy"] >= 0.90
    assert report["false_positive_rate_valid_to_nonvalid"] <= 0.05


def test_frozen_holdout_accepts_windows_crlf_checkout(tmp_path):
    windows_copy = tmp_path / "task1-holdout.csv"
    canonical = DATASET_PATH.read_bytes().replace(b"\r\n", b"\n")
    windows_copy.write_bytes(canonical.replace(b"\n", b"\r\n"))
    assert len(load_holdout(windows_copy)) == 300


def test_independent_syntax_reference_report_keeps_raw_and_policy_aligned_metrics():
    report = evaluate_reference()

    assert report["reference"] == "python-email-validator==2.3.0"
    assert report["corpus_size"] == 473
    assert report["agreement"] == 0.8943
    assert report["policy_aligned_agreement"] == 1.0
    assert report["mismatch_count"] == 50
    assert report["baseline_observation"]["initial_agreement"] == 0.8732


def test_malformed_punycode_alabel_is_rejected():
    result = validate_syntax("person@xn--0.example")

    assert not result.valid
    assert result.reason_codes == [ReasonCode.INVALID_DOMAIN]


def test_committed_holdout_reports_match_reproducible_results():
    holdout = json.loads((ROOT / "evaluation/task1-holdout-results.json").read_text(encoding="utf-8"))
    reference = json.loads(
        (ROOT / "evaluation/task1-syntax-reference-results.json").read_text(encoding="utf-8")
    )

    assert holdout["dataset_sha256"] == FROZEN_DATASET_SHA256
    assert holdout["accuracy"] == 1.0
    assert reference["corpus_sha256"] == "d7fba06c4ef11c2bfbdee8c02fe3bdc3e4ed04fb2e746b951d5cab6b0fbd5c01"
    assert reference["agreement"] == 0.8943
