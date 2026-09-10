import pytest

from app.reason_codes import ReasonCode
from app.syntax import validate_syntax


@pytest.mark.parametrize("email", ["user@example.com", "a.b+tag@gmail.com", "u@xn--bcher-kva.de"])
def test_valid_syntax(email: str):
    assert validate_syntax(email).valid


@pytest.mark.parametrize(
    ("email", "reason"),
    [
        ("", ReasonCode.EMPTY_EMAIL),
        ("userexample.com", ReasonCode.INVALID_SYNTAX),
        ("a@@example.com", ReasonCode.INVALID_SYNTAX),
        (".user@example.com", ReasonCode.INVALID_LOCAL_PART),
        ("user..name@example.com", ReasonCode.INVALID_LOCAL_PART),
        ("user@bad_domain.com", ReasonCode.INVALID_DOMAIN),
    ],
)
def test_invalid_syntax(email: str, reason: ReasonCode):
    assert reason in validate_syntax(email).reason_codes


def test_unicode_local_part_uses_controlled_smtputf8_subset():
    result = validate_syntax("e\u0301lif@bücher.example")
    assert result.valid
    assert result.normalized == "élif@xn--bcher-kva.example"
    assert result.requires_smtputf8 is True
    assert ReasonCode.INVALID_LOCAL_PART in validate_syntax(
        "élif@example.com", allow_smtputf8=False
    ).reason_codes
    assert ReasonCode.INVALID_LOCAL_PART in validate_syntax("user😀@example.com").reason_codes


def test_unicode_local_part_limit_is_measured_in_utf8_bytes():
    assert validate_syntax(f"{'é' * 32}@example.com").valid
    assert ReasonCode.LOCAL_PART_TOO_LONG in validate_syntax(
        f"{'é' * 33}@example.com"
    ).reason_codes
