from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from threading import Event

from app.blocklist.models import BlocklistHistoryReport, BlocklistRunResponse, MonitorHealth
from app.blocklist.service import BlocklistMonitorService


LOGGER = logging.getLogger(__name__)


class BlocklistScheduler:
    """Tek süreçli periyodik izleyici ve kalıcı kalp atışı yöneticisi."""

    def __init__(
        self,
        service: BlocklistMonitorService,
        *,
        monitor_name: str = "default",
        interval_seconds: int | None = None,
        grace_seconds: int | None = None,
        retention_days: int | None = None,
    ):
        self.service = service
        self.repository = service.repository
        self.monitor_name = monitor_name
        self.interval_seconds = interval_seconds or service.settings.blocklist_interval_seconds
        self.grace_seconds = grace_seconds or service.settings.blocklist_missed_grace_seconds
        self.retention_days = retention_days or service.settings.blocklist_retention_days
        if self.interval_seconds < 1:
            raise ValueError("Kontrol aralığı en az 1 saniye olmalıdır.")
        if self.retention_days < 30:
            raise ValueError("Blocklist geçmişi en az 30 gün saklanmalıdır.")

    def run_cycle(self, now: datetime | None = None) -> BlocklistRunResponse:
        started_at = now or datetime.now(UTC)
        self.repository.mark_monitor_started(
            self.monitor_name,
            self.interval_seconds,
            started_at,
        )
        try:
            report = self.service.run_once()
        except Exception as exc:
            self.repository.mark_monitor_failed(
                self.monitor_name,
                self.interval_seconds,
                f"{type(exc).__name__}: {exc}",
                datetime.now(UTC) if now is None else now,
            )
            raise
        completed_at = datetime.now(UTC) if now is None else now
        self.repository.mark_monitor_completed(
            self.monitor_name,
            self.interval_seconds,
            report.run_id,
            completed_at,
        )
        self.repository.delete_history_before(
            completed_at - timedelta(days=self.retention_days),
            self.monitor_name,
        )
        return report

    def status(self, now: datetime | None = None) -> MonitorHealth:
        return self.repository.get_monitor_health(
            self.monitor_name,
            self.interval_seconds,
            self.grace_seconds,
            now,
        )

    def history_report(
        self,
        days: int = 30,
        now: datetime | None = None,
    ) -> BlocklistHistoryReport:
        if not 1 <= days <= self.retention_days:
            raise ValueError(
                f"Rapor günü 1 ile {self.retention_days} arasında olmalıdır."
            )
        return self.repository.history_report(
            days,
            self.monitor_name,
            self.interval_seconds,
            self.grace_seconds,
            now,
        )

    def run_forever(self, stop_event: Event | None = None) -> None:
        stop_event = stop_event or Event()
        try:
            while not stop_event.is_set():
                try:
                    self.run_cycle()
                except Exception:
                    LOGGER.exception("Blocklist kontrol turu başarısız oldu.")
                if stop_event.wait(self.interval_seconds):
                    break
        finally:
            self.repository.mark_monitor_stopped(
                self.monitor_name,
                self.interval_seconds,
            )
