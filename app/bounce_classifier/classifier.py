import hashlib
import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from app.bounce_classifier.models import (
    ClassificationResult,
    Confidence,
    EventBatchClassificationResponse,
    EventCategory,
    NormalizedEvent,
    Permanence,
)
from app.bounce_classifier.privacy import (
    message_fingerprint,
    safe_event_id,
    safe_message_pattern,
    safe_recipient_identity,
)
from app.bounce_classifier.rules import ClassificationRule, load_rules, rule_matches
from app.config import DEFAULT_EMAIL_HASH_SECRET, PROJECT_ROOT


STATUS_RE = re.compile(r"(?<!\d)([245]\.\d{1,3}\.\d{1,3})(?!\d)")
SMTP_RE = re.compile(r"(?<!\d)([245]\d{2})(?!\d)")


class EventClassifier:
    def __init__(
        self,
        rules_path: Path | None = None,
        hash_secret: str = DEFAULT_EMAIL_HASH_SECRET,
    ):
        self.rules_path = rules_path or PROJECT_ROOT / "config" / "bounce_rules.json"
        self.hash_secret = hash_secret
        self.rules = load_rules(self.rules_path)

    @staticmethod
    def unwrap_sns(event: dict[str, Any]) -> dict[str, Any]:
        """SNS Notification zarfındaki SES JSON olayını güvenli biçimde açar."""
        message = event.get("Message")
        if not isinstance(message, str):
            return event
        try:
            inner = json.loads(message)
        except json.JSONDecodeError:
            return event
        if not isinstance(inner, dict) or not any(
            key in inner for key in ("notificationType", "eventType", "bounce", "complaint")
        ):
            return event
        unwrapped = dict(inner)
        if not any(key in unwrapped for key in ("event_id", "eventId")):
            message_id = event.get("MessageId")
            if message_id:
                unwrapped["event_id"] = message_id
        return unwrapped

    @classmethod
    def expand_recipients(cls, event: dict[str, Any]) -> list[dict[str, Any]]:
        """Çok alıcılı SES bildirimini alıcı başına bir mantıksal olaya böler."""
        event = cls.unwrap_sns(event)
        for container_name, recipients_name in (
            ("bounce", "bouncedRecipients"),
            ("complaint", "complainedRecipients"),
        ):
            container = event.get(container_name)
            recipients = container.get(recipients_name) if isinstance(container, dict) else None
            if not isinstance(recipients, list) or len(recipients) <= 1:
                continue
            mail = event.get("mail") if isinstance(event.get("mail"), dict) else {}
            base_id = str(
                event.get("event_id")
                or event.get("eventId")
                or mail.get("messageId")
                or hashlib.sha256(
                    json.dumps(event, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
                ).hexdigest()[:16]
            )
            expanded: list[dict[str, Any]] = []
            for index, recipient in enumerate(recipients, 1):
                if not isinstance(recipient, dict):
                    continue
                item = deepcopy(event)
                item[container_name][recipients_name] = [recipient]
                item["event_id"] = f"{base_id}:recipient:{index}"
                expanded.append(item)
            return expanded or [event]
        return [event]

    def normalize(self, event: dict[str, Any]) -> NormalizedEvent:
        event = self.unwrap_sns(event)
        bounce = event.get("bounce") if isinstance(event.get("bounce"), dict) else {}
        complaint = event.get("complaint") if isinstance(event.get("complaint"), dict) else {}
        mail = event.get("mail") if isinstance(event.get("mail"), dict) else {}
        recipients = bounce.get("bouncedRecipients", [])
        recipient = recipients[0] if recipients and isinstance(recipients[0], dict) else {}
        diagnostic = str(
            event.get("diagnostic_code")
            or event.get("diagnosticCode")
            or recipient.get("diagnosticCode")
            or ""
        )
        enhanced_status = str(
            event.get("enhanced_status")
            or event.get("status")
            or recipient.get("status")
            or ""
        )
        if not enhanced_status:
            status_match = STATUS_RE.search(diagnostic)
            enhanced_status = status_match.group(1) if status_match else ""
        smtp_code = str(event.get("smtp_code") or "")
        if not smtp_code:
            smtp_match = SMTP_RE.search(diagnostic)
            smtp_code = smtp_match.group(1) if smtp_match else ""
        event_type = str(
            event.get("event_type")
            or event.get("eventType")
            or event.get("notificationType")
            or "bounce"
        ).casefold()
        event_id = safe_event_id(str(
            event.get("event_id")
            or event.get("eventId")
            or mail.get("messageId")
            or hashlib.sha256(
                json.dumps(event, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()[:16]
        ), self.hash_secret)
        recipient_hash, recipient_domain = safe_recipient_identity(event, self.hash_secret)
        provider = str(event.get("provider") or "unknown").strip().casefold()
        if not re.fullmatch(r"[a-z0-9._-]{1,50}", provider):
            provider = "unknown"
        return NormalizedEvent(
            event_id=event_id,
            event_type=event_type,
            bounce_type=str(event.get("bounce_type") or bounce.get("bounceType") or "").casefold(),
            bounce_subtype=str(event.get("bounce_subtype") or bounce.get("bounceSubType") or "").casefold(),
            smtp_code=smtp_code,
            enhanced_status=enhanced_status.casefold(),
            diagnostic=diagnostic.casefold(),
            feedback_type=str(
                event.get("feedback_type")
                or complaint.get("complaintFeedbackType")
                or ""
            ).casefold(),
            provider=provider,
            recipient_hash=recipient_hash,
            recipient_domain=recipient_domain,
        )

    def classify(self, event: dict[str, Any]) -> ClassificationResult:
        expanded = self.expand_recipients(event)
        if len(expanded) > 1:
            raise ValueError(
                "Birden fazla alıcı içeren SES bildirimi classify_many veya toplu API ile işlenmelidir."
            )
        normalized = self.normalize(expanded[0])
        for rule in self.rules:
            if rule_matches(rule, normalized):
                return self._result(normalized, rule)
        pattern = safe_message_pattern(normalized.diagnostic) or "<empty>"
        return ClassificationResult(
            event_id=normalized.event_id,
            recipient_hash=normalized.recipient_hash,
            recipient_domain=normalized.recipient_domain,
            category=EventCategory.UNKNOWN,
            category_label="Bilinmeyen",
            subreason="Mevcut kurallarla eslesmeyen olay",
            recommended_action="Raporla ve yeni kural adayi olarak incele",
            confidence=Confidence.LOW,
            permanence=Permanence.UNKNOWN,
            rule_id="unknown_fallback",
            provider=normalized.provider,
            message_fingerprint=message_fingerprint(normalized.diagnostic),
            unknown_pattern=pattern,
        )

    @staticmethod
    def _result(event: NormalizedEvent, rule: ClassificationRule) -> ClassificationResult:
        return ClassificationResult(
            event_id=event.event_id,
            recipient_hash=event.recipient_hash,
            recipient_domain=event.recipient_domain,
            category=rule.category,
            category_label=rule.category_label,
            subreason=rule.subreason,
            recommended_action=rule.action,
            confidence=rule.confidence,
            permanence=rule.permanence,
            rule_id=rule.rule_id,
            provider=event.provider,
            message_fingerprint=message_fingerprint(event.diagnostic),
        )

    def classify_many(self, events: Iterable[dict[str, Any]]) -> EventBatchClassificationResponse:
        expanded = [item for event in events for item in self.expand_recipients(event)]
        results = [self.classify(event) for event in expanded]
        counts = Counter(result.category.value for result in results)
        unknown_count = counts.get(EventCategory.UNKNOWN.value, 0)
        return EventBatchClassificationResponse(
            total=len(results),
            category_counts=dict(sorted(counts.items())),
            unknown_rate=round(unknown_count / len(results), 4) if results else 0.0,
            results=results,
        )
