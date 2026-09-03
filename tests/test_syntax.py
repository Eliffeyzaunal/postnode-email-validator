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

