import hashlib
import hmac
import re
from typing import Any

# Tanı metinleri yalnızca RFC'ye tam uyan adresler içermeyebilir. Gizlilik
# katmanında dar bir doğrulama regex'i yerine @ içeren adres-benzeri parçaları
# ihtiyatlı biçimde maskeleriz. Böylece Unicode, tek etiketli alan adı ve tırnaklı
# yerel bölüm gibi biçimler de bilinmeyen örüntü raporuna sızmaz.
QUOTED_EMAIL_RE = re.compile(r'(?u)"[^"\r\n]{1,128}"@[^\s<>"\']{1,253}')
EMAIL_RE = re.compile(r"(?u)[^\s<>()\[\]{},;:\"']{1,128}@[^\s<>()\[\]{},;:\"']{1,253}")
IP_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
LONG_ID_RE = re.compile(r"(?i)\b(?:[a-f0-9]{12,}|\d{6,})\b")
WHITESPACE_RE = re.compile(r"\s+")
HASH_RE = re.compile(r"(?i)^[a-f0-9]{64}$")
DOMAIN_LABEL_RE = re.compile(r"(?i)^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def safe_message_pattern(value: str, *, max_length: int = 240) -> str:
    """Tanilama metnini kural analizi icin kisilestirilebilir veriden arindirir."""
    text = QUOTED_EMAIL_RE.sub("<email>", value)
    text = EMAIL_RE.sub("<email>", text)
    text = IP_RE.sub("<ip>", text)
    text = LONG_ID_RE.sub("<id>", text)
    text = WHITESPACE_RE.sub(" ", text.strip().casefold())
    return text[:max_length]


def message_fingerprint(value: str) -> str:
    return hashlib.sha256(safe_message_pattern(value).encode("utf-8")).hexdigest()


def _keyed_digest(value: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def safe_event_id(value: str, secret: str) -> str:
    value = value.strip()
    if "@" in value:
        return "hmac-sha256:" + _keyed_digest(value, secret)
    return value[:200]


def _safe_domain(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip().casefold().rstrip(".")
    if "@" in candidate:
        candidate = candidate.rsplit("@", 1)[1]
    try:
        ascii_domain = candidate.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    if not ascii_domain or len(ascii_domain) > 253:
        return None
    labels = ascii_domain.split(".")
    if any(not DOMAIN_LABEL_RE.fullmatch(label) for label in labels):
        return None
    return ascii_domain


def _first_recipient(event: dict[str, Any]) -> str | None:
    for container_name, list_name in (
        ("bounce", "bouncedRecipients"),
        ("complaint", "complainedRecipients"),
    ):
        container = event.get(container_name)
        items = container.get(list_name, []) if isinstance(container, dict) else []
        if items and isinstance(items[0], dict):
            value = items[0].get("emailAddress")
            if isinstance(value, str):
                return value
    mail = event.get("mail")
    destination = mail.get("destination", []) if isinstance(mail, dict) else []
    if destination and isinstance(destination[0], str):
        return destination[0]
    value = event.get("recipient")
    return value if isinstance(value, str) else None


def safe_recipient_identity(
    event: dict[str, Any],
    secret: str,
) -> tuple[str | None, str | None]:
    supplied_hash = event.get("recipient_hash")
    supplied_domain = event.get("recipient_domain")
    recipient = _first_recipient(event)
    recipient_digest = None
    if supplied_hash:
        candidate = str(supplied_hash).strip()
        recipient_digest = (
            candidate.casefold()
            if HASH_RE.fullmatch(candidate)
            else _keyed_digest(candidate, secret)
        )
    domain = _safe_domain(str(supplied_domain)) if supplied_domain else None
    if recipient and "@" in recipient:
        recipient_digest = recipient_digest or _keyed_digest(recipient.strip().casefold(), secret)
        domain = domain or _safe_domain(recipient.rsplit("@", 1)[1])
    return recipient_digest, domain
