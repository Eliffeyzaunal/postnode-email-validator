import re
from dataclasses import dataclass

from app.reason_codes import ReasonCode


LOCAL_PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")
LABEL_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


@dataclass(frozen=True)
class SyntaxResult:
    normalized: str | None
    local_part: str | None
    domain: str | None
    reason_codes: list[ReasonCode]

    @property
    def valid(self) -> bool:
        return not self.reason_codes


def validate_syntax(raw: str) -> SyntaxResult:
    value = raw.strip()
    if not value:
        return SyntaxResult(None, None, None, [ReasonCode.EMPTY_EMAIL])
    if len(value) > 254:
        return SyntaxResult(None, None, None, [ReasonCode.EMAIL_TOO_LONG])
    if value.count("@") != 1:
        return SyntaxResult(None, None, None, [ReasonCode.INVALID_SYNTAX])

    local, raw_domain = value.rsplit("@", 1)
    if not local or not raw_domain:
        return SyntaxResult(None, local or None, raw_domain or None, [ReasonCode.INVALID_SYNTAX])
    if len(local) > 64:
        return SyntaxResult(None, local, raw_domain.casefold(), [ReasonCode.LOCAL_PART_TOO_LONG])
    if (
        not LOCAL_PATTERN.fullmatch(local)
        or local.startswith(".")
        or local.endswith(".")
        or ".." in local
    ):
        return SyntaxResult(None, local, raw_domain.casefold(), [ReasonCode.INVALID_LOCAL_PART])

    try:
        domain = raw_domain.rstrip(".").encode("idna").decode("ascii").casefold()
    except UnicodeError:
        return SyntaxResult(None, local, raw_domain.casefold(), [ReasonCode.INVALID_DOMAIN])

    labels = domain.split(".")
    if (
        len(domain) > 253
        or len(labels) < 2
        or any(len(label) > 63 or not LABEL_PATTERN.fullmatch(label) for label in labels)
        or len(labels[-1]) < 2
    ):
        return SyntaxResult(None, local, domain, [ReasonCode.INVALID_DOMAIN])

    return SyntaxResult(f"{local}@{domain}", local, domain, [])

