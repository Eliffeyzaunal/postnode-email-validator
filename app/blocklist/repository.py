from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    event,
    insert,
    select,
    update,
)

from app.blocklist.models import (
    BlocklistCheckResult,
    BlocklistHistoryReport,
    BlocklistNotification,
    CheckStatus,
    MonitorHealth,
    NotificationType,
    ProviderHistorySummary,
)


metadata = MetaData()

blocklist_runs = Table(
    "blocklist_runs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("source_filename", String(255)),
    Column("started_at", DateTime, nullable=False),
    Column("completed_at", DateTime, nullable=False),
    Column("status", String(32), nullable=False),
    Column("total_checks", Integer, nullable=False),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

blocklist_results = Table(
    "blocklist_results",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "run_id",
        String(36),
        ForeignKey("blocklist_runs.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("asset_id", String(100), nullable=False),
    Column("asset_type", String(16), nullable=False),
    Column("asset_value", String(253), nullable=False),
    Column("provider_id", String(100), nullable=False),
    Column("provider_name", String(255), nullable=False),
    Column("status", String(32), nullable=False),
    Column("severity", String(16), nullable=False),
    Column("query_name", String(512)),
    Column("return_codes_json", JSON, nullable=False),
    Column("reasons_json", JSON, nullable=False),
    Column("removal_url", String(1024)),
    Column("checked_at", DateTime, nullable=False),
    Column("detail", Text),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)
Index(
    "idx_blocklist_results_run",
    blocklist_results.c.run_id,
    blocklist_results.c.asset_id,
    blocklist_results.c.provider_id,
)

blocklist_states = Table(
    "blocklist_states",
    metadata,
    Column("asset_id", String(100), primary_key=True),
    Column("provider_id", String(100), primary_key=True),
    Column("asset_type", String(16), nullable=False),
    Column("asset_value", String(253), nullable=False),
    Column("status", String(32), nullable=False),
    Column("first_detected_at", DateTime),
    Column("last_checked_at", DateTime, nullable=False),
    Column("last_changed_at", DateTime, nullable=False),
    Column("return_codes_json", JSON, nullable=False),
    Column("reason", Text),
    Column("removal_url", String(1024)),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

blocklist_notifications = Table(
    "blocklist_notifications",
    metadata,
    Column("id", String(36), primary_key=True),
    Column(
        "run_id",
        String(36),
        ForeignKey("blocklist_runs.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("event_type", String(32), nullable=False),
    Column("asset_id", String(100), nullable=False),
    Column("asset_type", String(16), nullable=False),
    Column("asset_value", String(253), nullable=False),
    Column("provider_id", String(100), nullable=False),
    Column("previous_status", String(32)),
    Column("current_status", String(32), nullable=False),
    Column("first_detected_at", DateTime),
    Column("reason", Text),
    Column("removal_url", String(1024)),
    Column("payload_json", JSON, nullable=False),
    Column("created_at", DateTime, nullable=False),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)
Index("idx_blocklist_notifications_run", blocklist_notifications.c.run_id)

blocklist_monitor_status = Table(
    "blocklist_monitor_status",
    metadata,
    Column("name", String(100), primary_key=True),
    Column("status", String(32), nullable=False),
    Column("interval_seconds", Integer, nullable=False),
    Column("last_started_at", DateTime),
    Column("last_completed_at", DateTime),
    Column("last_success_at", DateTime),
    Column("next_due_at", DateTime),
    Column("last_error", Text),
    Column("updated_at", DateTime, nullable=False),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

blocklist_monitor_events = Table(
    "blocklist_monitor_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("monitor_name", String(100), nullable=False),
    Column("event_type", String(32), nullable=False),
    Column("occurred_at", DateTime, nullable=False),
    Column("run_id", String(36)),
    Column("detail", Text),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)
Index(
    "idx_blocklist_monitor_events_time",
    blocklist_monitor_events.c.monitor_name,
    blocklist_monitor_events.c.occurred_at,
)


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _aware_utc(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=UTC) if value is not None else None


class BlocklistRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            future=True,
        )
        if self.engine.dialect.name == "sqlite":
            event.listen(self.engine, "connect", self._enable_sqlite_foreign_keys)
        if self.engine.dialect.name not in {"mysql", "sqlite"}:
            raise ValueError("Yalnızca MySQL (üretim) ve SQLite (test) desteklenir.")
        metadata.create_all(self.engine)

    @staticmethod
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    def close(self) -> None:
        self.engine.dispose()

    def save_run(
        self,
        run_id: str,
        source_filename: str | None,
        results: list[BlocklistCheckResult],
    ) -> list[BlocklistNotification]:
        started_at = min((item.checked_at for item in results), default=datetime.now(UTC))
        completed_at = datetime.now(UTC)
        notifications: list[BlocklistNotification] = []

        with self.engine.begin() as connection:
            connection.execute(
                insert(blocklist_runs).values(
                    id=run_id,
                    source_filename=source_filename,
                    started_at=_naive_utc(started_at),
                    completed_at=_naive_utc(completed_at),
                    status="completed",
                    total_checks=len(results),
                )
            )

            for result in results:
                previous = connection.execute(
                    select(blocklist_states).where(
                        blocklist_states.c.asset_id == result.asset_id,
                        blocklist_states.c.provider_id == result.provider_id,
                    )
                ).mappings().first()
                previous_status = (
                    CheckStatus(previous["status"]) if previous is not None else None
                )
                changed = previous_status != result.status
                first_detected_at = self._first_detected_at(
                    result, previous, previous_status
                )
                reason = (
                    result.reasons[0]
                    if result.reasons
                    else (
                        ", ".join(result.return_codes)
                        if result.return_codes
                        else result.detail
                    )
                )

                connection.execute(
                    insert(blocklist_results).values(
                        run_id=run_id,
                        asset_id=result.asset_id,
                        asset_type=result.asset_type.value,
                        asset_value=result.asset_value,
                        provider_id=result.provider_id,
                        provider_name=result.provider_name,
                        status=result.status.value,
                        severity=result.severity,
                        query_name=result.query_name,
                        return_codes_json=result.return_codes,
                        reasons_json=result.reasons,
                        removal_url=result.removal_url,
                        checked_at=_naive_utc(result.checked_at),
                        detail=result.detail,
                    )
                )

                state_values = {
                    "asset_type": result.asset_type.value,
                    "asset_value": result.asset_value,
                    "status": result.status.value,
                    "first_detected_at": first_detected_at,
                    "last_checked_at": _naive_utc(result.checked_at),
                    "last_changed_at": (
                        _naive_utc(result.checked_at)
                        if changed or previous is None
                        else previous["last_changed_at"]
                    ),
                    "return_codes_json": result.return_codes,
                    "reason": reason,
                    "removal_url": result.removal_url,
                }
                if previous is None:
                    connection.execute(
                        insert(blocklist_states).values(
                            asset_id=result.asset_id,
                            provider_id=result.provider_id,
                            **state_values,
                        )
                    )
                else:
                    connection.execute(
                        update(blocklist_states)
                        .where(
                            blocklist_states.c.asset_id == result.asset_id,
                            blocklist_states.c.provider_id == result.provider_id,
                        )
                        .values(**state_values)
                    )

                event_type = self._notification_type(previous_status, result.status)
                if event_type is not None:
                    notification_first_detected = first_detected_at
                    notification_reason = reason
                    if (
                        event_type == NotificationType.DELISTED
                        and previous is not None
                    ):
                        if previous["first_detected_at"] is not None:
                            notification_first_detected = previous["first_detected_at"]
                        if previous["reason"]:
                            notification_reason = previous["reason"]
                    notification = BlocklistNotification(
                        id=str(uuid.uuid4()),
                        run_id=run_id,
                        type=event_type,
                        asset_id=result.asset_id,
                        asset_type=result.asset_type,
                        asset_value=result.asset_value,
                        provider_id=result.provider_id,
                        previous_status=previous_status,
                        current_status=result.status,
                        first_detected_at=_aware_utc(notification_first_detected),
                        reason=notification_reason,
                        removal_url=result.removal_url,
                        created_at=completed_at,
                    )
                    notifications.append(notification)
                    connection.execute(
                        insert(blocklist_notifications).values(
                            id=notification.id,
                            run_id=run_id,
                            event_type=notification.type.value,
                            asset_id=notification.asset_id,
                            asset_type=notification.asset_type.value,
                            asset_value=notification.asset_value,
                            provider_id=notification.provider_id,
                            previous_status=(
                                notification.previous_status.value
                                if notification.previous_status
                                else None
                            ),
                            current_status=notification.current_status.value,
                            first_detected_at=notification_first_detected,
                            reason=notification.reason,
                            removal_url=notification.removal_url,
                            payload_json=notification.model_dump(mode="json"),
                            created_at=_naive_utc(notification.created_at),
                        )
                    )
        return notifications

    @staticmethod
    def _first_detected_at(
        result: BlocklistCheckResult,
        previous: Any,
        previous_status: CheckStatus | None,
    ) -> datetime | None:
        if result.status != CheckStatus.LISTED:
            return None
        if (
            previous is not None
            and previous_status == CheckStatus.LISTED
            and previous["first_detected_at"] is not None
        ):
            return previous["first_detected_at"]
        return _naive_utc(result.checked_at)

    @staticmethod
    def _notification_type(
        previous: CheckStatus | None, current: CheckStatus
    ) -> NotificationType | None:
        if previous == current:
            return None
        if current == CheckStatus.LISTED:
            return NotificationType.LISTED
        if previous == CheckStatus.LISTED and current == CheckStatus.NOT_LISTED:
            return NotificationType.DELISTED
        if current == CheckStatus.QUERY_ERROR:
            return NotificationType.QUERY_ERROR
        if previous == CheckStatus.QUERY_ERROR and current == CheckStatus.NOT_LISTED:
            return NotificationType.RECOVERED
        return None

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            run = connection.execute(
                select(blocklist_runs).where(blocklist_runs.c.id == run_id)
            ).mappings().first()
            if run is None:
                return None
            result_rows = connection.execute(
                select(blocklist_results)
                .where(blocklist_results.c.run_id == run_id)
                .order_by(blocklist_results.c.id)
            ).mappings().all()
        return {
            "run_id": run["id"],
            "source_filename": run["source_filename"],
            "status": run["status"],
            "started_at": _aware_utc(run["started_at"]).isoformat(),
            "completed_at": _aware_utc(run["completed_at"]).isoformat(),
            "total_checks": run["total_checks"],
            "results": [self._result_dict(row) for row in result_rows],
        }

    def get_notifications(self, run_id: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(blocklist_notifications)
                .where(blocklist_notifications.c.run_id == run_id)
                .order_by(blocklist_notifications.c.created_at)
            ).mappings().all()
        return [dict(row["payload_json"]) for row in rows]

    @staticmethod
    def _result_dict(row: Any) -> dict[str, Any]:
        return {
            "asset_id": row["asset_id"],
            "asset_type": row["asset_type"],
            "asset_value": row["asset_value"],
            "provider_id": row["provider_id"],
            "provider_name": row["provider_name"],
            "status": row["status"],
            "severity": row["severity"],
            "query_name": row["query_name"],
            "return_codes": row["return_codes_json"],
            "reasons": row["reasons_json"],
            "removal_url": row["removal_url"],
            "checked_at": _aware_utc(row["checked_at"]).isoformat(),
            "detail": row["detail"],
        }

    def delete_run(self, run_id: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(delete(blocklist_runs).where(blocklist_runs.c.id == run_id))

    def delete_states(self, asset_ids: list[str]) -> None:
        if not asset_ids:
            return
        with self.engine.begin() as connection:
            connection.execute(
                delete(blocklist_states).where(blocklist_states.c.asset_id.in_(asset_ids))
            )

    def mark_monitor_started(
        self,
        name: str,
        interval_seconds: int,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now(UTC)
        self._update_monitor(
            name=name,
            status="running",
            interval_seconds=interval_seconds,
            now=now,
            last_started_at=now,
            next_due_at=now + timedelta(seconds=interval_seconds),
            event_type="started",
        )

    def mark_monitor_completed(
        self,
        name: str,
        interval_seconds: int,
        run_id: str,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now(UTC)
        self._update_monitor(
            name=name,
            status="healthy",
            interval_seconds=interval_seconds,
            now=now,
            last_completed_at=now,
            last_success_at=now,
            next_due_at=now + timedelta(seconds=interval_seconds),
            last_error=None,
            event_type="completed",
            run_id=run_id,
        )

    def mark_monitor_failed(
        self,
        name: str,
        interval_seconds: int,
        detail: str,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now(UTC)
        self._update_monitor(
            name=name,
            status="error",
            interval_seconds=interval_seconds,
            now=now,
            last_completed_at=now,
            next_due_at=now + timedelta(seconds=interval_seconds),
            last_error=detail,
            event_type="failed",
            detail=detail,
        )

    def mark_monitor_stopped(
        self,
        name: str,
        interval_seconds: int,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now(UTC)
        self._update_monitor(
            name=name,
            status="stopped",
            interval_seconds=interval_seconds,
            now=now,
            event_type="stopped",
        )

    def _update_monitor(
        self,
        *,
        name: str,
        status: str,
        interval_seconds: int,
        now: datetime,
        event_type: str,
        last_started_at: datetime | None = None,
        last_completed_at: datetime | None = None,
        last_success_at: datetime | None = None,
        next_due_at: datetime | None = None,
        last_error: str | None = None,
        run_id: str | None = None,
        detail: str | None = None,
    ) -> None:
        now_db = _naive_utc(now)
        with self.engine.begin() as connection:
            previous = connection.execute(
                select(blocklist_monitor_status).where(
                    blocklist_monitor_status.c.name == name
                )
            ).mappings().first()
            values = {
                "status": status,
                "interval_seconds": interval_seconds,
                "updated_at": now_db,
            }
            optional_values = {
                "last_started_at": last_started_at,
                "last_completed_at": last_completed_at,
                "last_success_at": last_success_at,
                "next_due_at": next_due_at,
            }
            for key, value in optional_values.items():
                if value is not None:
                    values[key] = _naive_utc(value)
            if event_type in {"completed", "failed"}:
                values["last_error"] = last_error
            if previous is None:
                connection.execute(
                    insert(blocklist_monitor_status).values(name=name, **values)
                )
            else:
                connection.execute(
                    update(blocklist_monitor_status)
                    .where(blocklist_monitor_status.c.name == name)
                    .values(**values)
                )
            connection.execute(
                insert(blocklist_monitor_events).values(
                    monitor_name=name,
                    event_type=event_type,
                    occurred_at=now_db,
                    run_id=run_id,
                    detail=detail,
                )
            )

    def get_monitor_health(
        self,
        name: str,
        interval_seconds: int,
        grace_seconds: int,
        now: datetime | None = None,
    ) -> MonitorHealth:
        now = now or datetime.now(UTC)
        with self.engine.connect() as connection:
            row = connection.execute(
                select(blocklist_monitor_status).where(
                    blocklist_monitor_status.c.name == name
                )
            ).mappings().first()
        if row is None:
            return MonitorHealth(
                name=name,
                status="not_started",
                interval_seconds=interval_seconds,
                missed=True,
                checked_at=now,
            )
        next_due = _aware_utc(row["next_due_at"])
        missed = bool(
            next_due
            and now > next_due + timedelta(seconds=grace_seconds)
            and row["status"] != "stopped"
        )
        return MonitorHealth(
            name=name,
            status="missed" if missed else row["status"],
            interval_seconds=row["interval_seconds"],
            last_started_at=_aware_utc(row["last_started_at"]),
            last_completed_at=_aware_utc(row["last_completed_at"]),
            last_success_at=_aware_utc(row["last_success_at"]),
            next_due_at=next_due,
            last_error=row["last_error"],
            missed=missed,
            checked_at=now,
        )

    def history_report(
        self,
        days: int,
        monitor_name: str,
        interval_seconds: int,
        grace_seconds: int,
        now: datetime | None = None,
    ) -> BlocklistHistoryReport:
        now = now or datetime.now(UTC)
        start = now - timedelta(days=days)
        start_db = _naive_utc(start)
        end_db = _naive_utc(now + timedelta(seconds=1))
        with self.engine.connect() as connection:
            runs = connection.execute(
                select(blocklist_runs.c.id).where(
                    blocklist_runs.c.completed_at >= start_db,
                    blocklist_runs.c.completed_at <= end_db,
                )
            ).all()
            result_rows = connection.execute(
                select(
                    blocklist_results.c.provider_id,
                    blocklist_results.c.status,
                ).where(
                    blocklist_results.c.checked_at >= start_db,
                    blocklist_results.c.checked_at <= end_db,
                )
            ).mappings().all()
            notification_rows = connection.execute(
                select(blocklist_notifications.c.event_type).where(
                    blocklist_notifications.c.created_at >= start_db,
                    blocklist_notifications.c.created_at <= end_db,
                )
            ).mappings().all()
            current_rows = connection.execute(
                select(blocklist_states).where(
                    blocklist_states.c.status == CheckStatus.LISTED.value
                )
            ).mappings().all()

        by_provider: dict[str, Counter] = defaultdict(Counter)
        for row in result_rows:
            by_provider[row["provider_id"]][row["status"]] += 1
        providers = []
        for provider_id, counts in sorted(by_provider.items()):
            total = sum(counts.values())
            successful = counts[CheckStatus.LISTED.value] + counts[CheckStatus.NOT_LISTED.value]
            providers.append(
                ProviderHistorySummary(
                    provider_id=provider_id,
                    total_checks=total,
                    listed=counts[CheckStatus.LISTED.value],
                    not_listed=counts[CheckStatus.NOT_LISTED.value],
                    query_error=counts[CheckStatus.QUERY_ERROR.value],
                    unavailable=counts[CheckStatus.UNAVAILABLE.value],
                    availability_rate=round(successful / total, 4) if total else 0.0,
                )
            )
        event_counts = Counter(row["event_type"] for row in notification_rows)
        current_listings = [
            {
                "asset_id": row["asset_id"],
                "asset_type": row["asset_type"],
                "asset_value": row["asset_value"],
                "provider_id": row["provider_id"],
                "first_detected_at": (
                    _aware_utc(row["first_detected_at"]).isoformat()
                    if row["first_detected_at"]
                    else None
                ),
                "reason": row["reason"],
                "removal_url": row["removal_url"],
            }
            for row in current_rows
        ]
        return BlocklistHistoryReport(
            days=days,
            period_start=start,
            period_end=now,
            total_runs=len(runs),
            total_checks=len(result_rows),
            notifications=len(notification_rows),
            listed_events=event_counts[NotificationType.LISTED.value],
            delisted_events=event_counts[NotificationType.DELISTED.value],
            query_error_events=event_counts[NotificationType.QUERY_ERROR.value],
            providers=providers,
            current_listings=current_listings,
            monitor=self.get_monitor_health(
                monitor_name,
                interval_seconds,
                grace_seconds,
                now,
            ),
        )

    def delete_history_before(self, cutoff: datetime, monitor_name: str) -> None:
        cutoff_db = _naive_utc(cutoff)
        with self.engine.begin() as connection:
            connection.execute(
                delete(blocklist_runs).where(blocklist_runs.c.completed_at < cutoff_db)
            )
            connection.execute(
                delete(blocklist_monitor_events).where(
                    blocklist_monitor_events.c.monitor_name == monitor_name,
                    blocklist_monitor_events.c.occurred_at < cutoff_db,
                )
            )

    def delete_monitor(self, name: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                delete(blocklist_monitor_events).where(
                    blocklist_monitor_events.c.monitor_name == name
                )
            )
            connection.execute(
                delete(blocklist_monitor_status).where(
                    blocklist_monitor_status.c.name == name
                )
            )
