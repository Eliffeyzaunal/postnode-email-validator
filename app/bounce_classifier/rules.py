import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.bounce_classifier.models import Confidence, EventCategory, NormalizedEvent, Permanence


LIST_MATCH_FIELDS = {
    "event_types",
    "bounce_types",
    "bounce_subtypes",
    "feedback_types",
    "smtp_codes",
    "providers",
    "enhanced_status_prefixes",
}
REGEX_MATCH_FIELDS = {"diagnostic_regex", "diagnostic_not_regex"}
ALLOWED_MATCH_FIELDS = LIST_MATCH_FIELDS | REGEX_MATCH_FIELDS


@dataclass(frozen=True)
class ClassificationRule:
    rule_id: str
    priority: int
    category: EventCategory
    category_label: str
    subreason: str
    action: str
    confidence: Confidence
    permanence: Permanence
    providers: tuple[str, ...]
    sources: tuple[str, ...]
    match: dict[str, Any]
    example_message: str
    trigger_example: dict[str, Any]
    counter_example: dict[str, Any]


def load_rules(path: Path) -> list[ClassificationRule]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("rules"), list):
        raise ValueError("Kural dosyasinin kokunde bir rules listesi bulunmalidir.")
    if payload.get("schema_version") != 1:
        raise ValueError("Desteklenmeyen bounce kural semasi; schema_version 1 olmalidir.")
    rules: list[ClassificationRule] = []
    seen_ids: set[str] = set()
    seen_priorities: set[int] = set()
    for raw in payload["rules"]:
        if not isinstance(raw, dict):
            raise ValueError("Her kural bir JSON nesnesi olmalidir.")
        rule_id = str(raw["id"])
        priority = int(raw["priority"])
        if rule_id in seen_ids:
            raise ValueError(f"Yinelenen kural kimligi: {rule_id}")
        if priority in seen_priorities:
            raise ValueError(f"Yinelenen kural onceligi: {priority}")
        seen_ids.add(rule_id)
        seen_priorities.add(priority)
        match_value = raw.get("match")
        if not isinstance(match_value, dict) or not match_value:
            raise ValueError(f"Kural en az bir eslesme kosulu icermelidir: {rule_id}")
        match = dict(match_value)
        unsupported = sorted(set(match) - ALLOWED_MATCH_FIELDS)
        if unsupported:
            raise ValueError(
                f"Desteklenmeyen eslesme alani ({rule_id}): {', '.join(unsupported)}"
            )
        for key in LIST_MATCH_FIELDS & set(match):
            value = match[key]
            if not isinstance(value, list) or not value or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                raise ValueError(f"{rule_id}.{key} bos olmayan bir metin listesi olmalidir.")
        for key in REGEX_MATCH_FIELDS & set(match):
            value = match[key]
            if not isinstance(value, str) or not value:
                raise ValueError(f"{rule_id}.{key} bos olmayan bir regex metni olmalidir.")
            re.compile(value, re.IGNORECASE)
        providers = raw.get("providers")
        sources = raw.get("sources")
        for key, value in (("providers", providers), ("sources", sources)):
            if not isinstance(value, list) or not value or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                raise ValueError(f"{rule_id}.{key} bos olmayan bir metin listesi olmalidir.")
        for key in ("category_label", "subreason", "action", "example_message"):
            if not isinstance(raw.get(key), str) or not raw[key].strip():
                raise ValueError(f"{rule_id}.{key} bos olmayan bir metin olmalidir.")
        for key in ("trigger_example", "counter_example"):
            if not isinstance(raw.get(key), dict):
                raise ValueError(f"{rule_id}.{key} bir JSON nesnesi olmalidir.")
        rules.append(
            ClassificationRule(
                rule_id=rule_id,
                priority=priority,
                category=EventCategory(raw["category"]),
                category_label=str(raw["category_label"]),
                subreason=str(raw["subreason"]),
                action=str(raw["action"]),
                confidence=Confidence(raw["confidence"]),
                permanence=Permanence(raw["permanence"]),
                providers=tuple(providers),
                sources=tuple(sources),
                match=match,
                example_message=str(raw["example_message"]),
                trigger_example=dict(raw["trigger_example"]),
                counter_example=dict(raw["counter_example"]),
            )
        )
    if not rules:
        raise ValueError("Kural dosyasinda en az bir kural bulunmalidir.")
    return sorted(rules, key=lambda item: item.priority)


def _in(value: str, choices: list[str]) -> bool:
    return value.casefold() in {str(choice).casefold() for choice in choices}


def rule_matches(rule: ClassificationRule, event: NormalizedEvent) -> bool:
    match = rule.match
    exact_fields = {
        "event_types": event.event_type,
        "bounce_types": event.bounce_type,
        "bounce_subtypes": event.bounce_subtype,
        "feedback_types": event.feedback_type,
        "smtp_codes": event.smtp_code,
        "providers": event.provider,
    }
    for key, value in exact_fields.items():
        if key in match and not _in(value, match[key]):
            return False
    prefixes = match.get("enhanced_status_prefixes")
    if prefixes and not any(event.enhanced_status.startswith(str(prefix)) for prefix in prefixes):
        return False
    pattern = match.get("diagnostic_regex")
    if pattern and not re.search(str(pattern), event.diagnostic, re.IGNORECASE):
        return False
    negative_pattern = match.get("diagnostic_not_regex")
    if negative_pattern and re.search(str(negative_pattern), event.diagnostic, re.IGNORECASE):
        return False
    return True
