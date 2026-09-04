from __future__ import annotations

import ipaddress
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AssetType(StrEnum):
    IP = "ip"
    DOMAIN = "domain"


class Availability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class DNSResponseState(StrEnum):
    OK = "ok"
    NXDOMAIN = "nxdomain"
    TIMEOUT = "timeout"
    SERVFAIL = "servfail"
    REFUSED = "refused"
    ERROR = "error"


class CheckStatus(StrEnum):
    LISTED = "listed"
    NOT_LISTED = "not_listed"
    QUERY_ERROR = "query_error"
    UNAVAILABLE = "unavailable"


class NotificationType(StrEnum):
    LISTED = "listed"
    DELISTED = "delisted"
    QUERY_ERROR = "query_error"
    RECOVERED = "recovered"


class MonitoredAsset(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    type: AssetType
    value: str = Field(min_length=1, max_length=253)
    label: str | None = Field(default=None, max_length=255)

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str, info):
        normalized = value.strip().casefold().rstrip(".")
        asset_type = info.data.get("type")
        if asset_type == AssetType.IP:
            ipaddress.ip_address(normalized)
        elif asset_type == AssetType.DOMAIN:
            if len(normalized) > 253 or not normalized:
                raise ValueError("Geçerli bir alan adı gereklidir.")
            if normalized != "test" and (
                "." not in normalized
                or any(not label or len(label) > 63 for label in normalized.split("."))
            ):
                raise ValueError("Geçerli bir alan adı gereklidir.")
        return normalized


class ProviderDefinition(BaseModel):
    id: str
    name: str
    asset_types: list[AssetType]
    availability: Availability
    zone: str | None = None
    query_mode: Literal["reverse_ip", "domain"] | None = None
    severity: Literal["info", "low", "medium", "high"] = "medium"
    return_codes: dict[str, str] = Field(default_factory=dict)
    bitmask_codes: dict[str, str] = Field(default_factory=dict)
    error_codes: dict[str, str] = Field(default_factory=dict)
    removal_url: str | None = None
    source_url: str
    unavailable_reason: str | None = None


class DNSResponse(BaseModel):
    state: DNSResponseState
    a_records: list[str] = Field(default_factory=list)
    txt_records: list[str] = Field(default_factory=list)
    detail: str | None = None


class BlocklistCheckResult(BaseModel):
    asset_id: str
    asset_type: AssetType
    asset_value: str
    provider_id: str
    provider_name: str
    status: CheckStatus
    severity: str
    query_name: str | None = None
    return_codes: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    removal_url: str | None = None
    checked_at: datetime
    detail: str | None = None


class BlocklistNotification(BaseModel):
    id: str
    run_id: str
    type: NotificationType
    asset_id: str
    asset_type: AssetType
    asset_value: str
    provider_id: str
    previous_status: CheckStatus | None = None
    current_status: CheckStatus
    first_detected_at: datetime | None = None
    reason: str | None = None
    removal_url: str | None = None
    created_at: datetime


class BlocklistSummary(BaseModel):
    total: int
    listed: int
    not_listed: int
    query_error: int
    unavailable: int


class BlocklistRunResponse(BaseModel):
    run_id: str
    source_filename: str | None = None
    summary: BlocklistSummary
    results: list[BlocklistCheckResult]
    notifications: list[BlocklistNotification]


class BlocklistCheckRequest(BaseModel):
    assets: list[MonitoredAsset] | None = Field(default=None, max_length=1000)


class MonitorHealth(BaseModel):
    name: str
    status: Literal["not_started", "running", "healthy", "error", "missed", "stopped"]
    interval_seconds: int
    last_started_at: datetime | None = None
    last_completed_at: datetime | None = None
    last_success_at: datetime | None = None
    next_due_at: datetime | None = None
    last_error: str | None = None
    missed: bool
    checked_at: datetime


class ProviderHistorySummary(BaseModel):
    provider_id: str
    total_checks: int
    listed: int
    not_listed: int
    query_error: int
    unavailable: int
    availability_rate: float


class BlocklistHistoryReport(BaseModel):
    days: int
    period_start: datetime
    period_end: datetime
    total_runs: int
    total_checks: int
    notifications: int
    listed_events: int
    delisted_events: int
    query_error_events: int
    providers: list[ProviderHistorySummary]
    current_listings: list[dict]
    monitor: MonitorHealth
