from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventCategory(StrEnum):
    PERMANENT_INVALID_ADDRESS = "permanent_invalid_address"
    MAILBOX_FULL = "mailbox_full"
    TEMPORARY_SERVER_ERROR = "temporary_server_error"
    CONTENT_POLICY_REJECTION = "content_policy_rejection"
    BLOCKLIST_REJECTION = "blocklist_rejection"
    REPUTATION_RATE_LIMIT = "reputation_rate_limit"
    AUTOMATIC_RESPONSE = "automatic_response"
    COMPLAINT = "complaint"
    UNKNOWN = "unknown"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Permanence(StrEnum):
    PERMANENT = "permanent"
    TRANSIENT = "transient"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class NormalizedEvent:
    event_id: str
    event_type: str
    bounce_type: str
    bounce_subtype: str
    smtp_code: str
    enhanced_status: str
    diagnostic: str
    feedback_type: str
    provider: str
    recipient_hash: str | None
    recipient_domain: str | None


class ClassificationResult(BaseModel):
    event_id: str
    recipient_hash: str | None = None
    recipient_domain: str | None = None
    category: EventCategory
    category_label: str
    subreason: str
    recommended_action: str
    confidence: Confidence
    permanence: Permanence
    rule_id: str
    provider: str
    message_fingerprint: str
    unknown_pattern: str | None = None


class EventClassificationRequest(BaseModel):
    event: dict[str, Any]


class EventBatchClassificationRequest(BaseModel):
    events: list[dict[str, Any]] = Field(min_length=1, max_length=1_000)


class EventBatchClassificationResponse(BaseModel):
    total: int
    category_counts: dict[str, int]
    unknown_rate: float
    results: list[ClassificationResult]
