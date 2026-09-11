import re
import unicodedata
from dataclasses import dataclass

import idna

from app.reason_codes import ReasonCode


LOCAL_PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")
LABEL_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


@dataclass(frozen=True)
class SyntaxResult:
    normalized: str | None
    local_part: str | None
    domain: str | None
    reason_codes: list[ReasonCode]
    requires_smtputf8: bool = False

    @property
    def valid(self) -> bool:
        return not self.reason_codes


def _valid_unicode_local(local: str) -> bool:
    """Allow a conservative SMTPUTF8 dot-atom subset: letters, marks and digits."""
    for character in local:
        if ord(character) < 128:
            if not LOCAL_PATTERN.fullmatch(character):
                return False
        elif unicodedata.category(character)[0] not in {"L", "M", "N"}:
            return False
    return True


def validate_syntax(raw: str, allow_smtputf8: bool = True) -> SyntaxResult:
    value = raw.strip()
    if not value:
        return SyntaxResult(None, None, None, [ReasonCode.EMPTY_EMAIL])
    if value.count("@") != 1:
        return SyntaxResult(None, None, None, [ReasonCode.INVALID_SYNTAX])

    local, raw_domain = value.rsplit("@", 1)
    local = unicodedata.normalize("NFC", local)
    if not local or not raw_domain:
        return SyntaxResult(None, local or None, raw_domain or None, [ReasonCode.INVALID_SYNTAX])
    requires_smtputf8 = not local.isascii()
    if len(local.encode("utf-8")) > 64:
        return SyntaxResult(None, local, raw_domain.casefold(), [ReasonCode.LOCAL_PART_TOO_LONG])
    if (
        (requires_smtputf8 and (not allow_smtputf8 or not _valid_unicode_local(local)))
        or (not requires_smtputf8 and not LOCAL_PATTERN.fullmatch(local))
        or local.startswith(".")
        or local.endswith(".")
        or ".." in local
    ):
        return SyntaxResult(None, local, raw_domain.casefold(), [ReasonCode.INVALID_LOCAL_PART])

    try:
        # The stdlib codec can pass malformed pre-encoded A-labels through.
        # idna.encode validates both Unicode labels and existing ``xn--`` labels.
        domain = idna.encode(raw_domain.rstrip("."), uts46=True).decode("ascii").casefold()
    except (idna.IDNAError, UnicodeError):
        return SyntaxResult(None, local, raw_domain.casefold(), [ReasonCode.INVALID_DOMAIN])

    labels = domain.split(".")
    normalized = f"{local}@{domain}"
    if len(normalized.encode("utf-8")) > 254:
        return SyntaxResult(None, local, domain, [ReasonCode.EMAIL_TOO_LONG])
    if (
        len(domain) > 253
        or len(labels) < 2
        or any(len(label) > 63 or not LABEL_PATTERN.fullmatch(label) for label in labels)
        or len(labels[-1]) < 2
    ):
        return SyntaxResult(None, local, domain, [ReasonCode.INVALID_DOMAIN])

    return SyntaxResult(normalized, local, domain, [], requires_smtputf8)
