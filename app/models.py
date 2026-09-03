from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.reason_codes import ReasonCode


class Status(StrEnum):
    VALID = "gecerli"
    SUSPICIOUS = "supheli"
    INVALID = "gecersiz"


class DNSState(StrEnum):
    MX = "mx"
    A_FALLBACK = "a_fallback"
    NO_MAIL_HOST = "no_mail_host"
    NXDOMAIN = "nxdomain"
    ERROR = "error"


@dataclass(frozen=True)
class DNSResult:
    domain: str
    state: DNSState
    detail: str | None = None
    from_cache: bool = False


@dataclass
class InternalResult:
    row_number: int
    original: str
    normalized: str | None
    domain: str | None
    local_part: str | None
    status: Status
    reason_codes: list[ReasonCode] = field(default_factory=list)
    suggestion: str | None = None


class EmailRequest(BaseModel):
    email: str = Field(max_length=1000, examples=["kullanici@gmail.com"])


class BatchRequest(BaseModel):
    emails: list[str] = Field(min_length=1, max_length=10_000)


class ResultResponse(BaseModel):
    row_number: int
    masked_email: str
    email_hash: str
    domain: str | None
    status: Status
    reason_codes: list[ReasonCode]
    suggestion: str | None = None


class SummaryResponse(BaseModel):
    total: int
    valid: int
    suspicious: int
    invalid: int
    estimated_bounce_rate: float
    top_domains: dict[str, int]
    duration_ms: float


class BatchResponse(BaseModel):
    batch_id: str
    filename: str | None = None
    summary: SummaryResponse
    results: list[ResultResponse]


class BatchMetadataResponse(BaseModel):
    batch_id: str
    filename: str | None
    created_at: str
    summary: dict[str, Any]

