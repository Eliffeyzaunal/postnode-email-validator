import importlib.util
import json

from app.config import PROJECT_ROOT

SCRIPT = PROJECT_ROOT / "scripts" / "evaluate_bounce_automated.py"
SPEC = importlib.util.spec_from_file_location("evaluate_bounce_automated", SCRIPT)
auto = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(auto)


def test_committed_dataset_meets_automatic_acceptance():
    metrics = auto.evaluate_automated(
        PROJECT_ROOT / "evaluation" / "bounce-evaluation.jsonl"
    )

    assert metrics["dataset_size"] == 360
    assert metrics["specification_accuracy"] >= 0.90
    assert metrics["automated_acceptance"]["all_required_categories_present"] is True
    assert metrics["automated_acceptance"]["no_clear_email_in_dataset"] is True
    assert metrics["automated_acceptance"]["all_rule_trigger_examples_pass"] is True
    assert metrics["automated_acceptance"]["all_rule_counter_examples_pass"] is True
    assert metrics["automated_acceptance"]["no_transient_event_classified_as_permanent"] is True
    assert metrics["automated_acceptance"]["acceptance_met"] is True
    assert metrics["customer_accuracy_claim"] is False


def test_rule_fixture_validation_covers_all_loaded_rules():
    metrics = auto.evaluate_automated(
        PROJECT_ROOT / "evaluation" / "bounce-evaluation.jsonl"
    )

    fixture = metrics["rule_fixture_validation"]
    assert fixture["rule_count"] >= 20
    assert fixture["trigger_failures"] == []
    assert fixture["counter_failures"] == []


def test_require_acceptance_returns_nonzero_for_too_small_dataset(tmp_path):
    source = PROJECT_ROOT / "evaluation" / "bounce-evaluation.jsonl"
    lines = [line for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    small = tmp_path / "small.jsonl"
    small.write_text("\n".join(lines[:20]) + "\n", encoding="utf-8")

    code = auto.main([
        "--dataset", str(small),
        "--output", str(tmp_path / "result.json"),
        "--markdown", str(tmp_path / "report.md"),
        "--require-acceptance",
    ])
    assert code == 2


def test_dataset_with_clear_email_is_not_accepted(tmp_path):
    source = PROJECT_ROOT / "evaluation" / "bounce-evaluation.jsonl"
    first = json.loads(source.read_text(encoding="utf-8").splitlines()[0])
    first["event"]["diagnostic_code"] = "recipient user@example.com rejected"

    bad = tmp_path / "pii.jsonl"
    bad.write_text(json.dumps(first) + "\n", encoding="utf-8")

    metrics = auto.evaluate_automated(bad)

    assert metrics["automated_acceptance"]["no_clear_email_in_dataset"] is False
    assert metrics["automated_acceptance"]["acceptance_met"] is False
