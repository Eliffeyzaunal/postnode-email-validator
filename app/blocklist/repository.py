from __future__ import annotations

import uuid
from datetime import UTC, datetime
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
    BlocklistNotification,
    CheckStatus,
    NotificationType,
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
                    ", ".join(result.return_codes)
                    if result.return_codes
                    else (result.reasons[0] if result.reasons else result.detail)
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
                    if (
                        event_type == NotificationType.DELISTED
                        and previous is not None
                        and previous["first_detected_at"] is not None
                    ):
                        notification_first_detected = previous["first_detected_at"]
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
                        reason=reason,
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
