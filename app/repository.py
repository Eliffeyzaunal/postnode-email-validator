from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    Column,
    create_engine,
    delete,
    event,
    func,
    insert,
    select,
)
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine

from app.models import DNSResult, DNSState, InternalResult
from app.privacy import email_hash, mask_email


metadata = MetaData()

dns_cache = Table(
    "dns_cache",
    metadata,
    Column("domain", String(253), primary_key=True),
    Column("state", String(32), nullable=False),
    Column("detail", Text),
    Column("checked_at", DateTime, nullable=False),
    Column("expires_at", DateTime, nullable=False, index=True),
)

batches = Table(
    "batches",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("filename", String(255)),
    Column("created_at", DateTime, nullable=False),
    Column("summary_json", JSON, nullable=False),
)

validation_results = Table(
    "validation_results",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("batch_id", String(36), ForeignKey("batches.id", ondelete="CASCADE"), nullable=False),
    Column("row_number", Integer, nullable=False),
    Column("email_hash", String(64), nullable=False),
    Column("masked_email", String(320), nullable=False),
    Column("domain", String(253)),
    Column("status", String(16), nullable=False),
    Column("reason_codes_json", JSON, nullable=False),
    Column("suggestion", String(320)),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)
Index("idx_results_batch", validation_results.c.batch_id, validation_results.c.row_number)


def _utc_naive(value: datetime) -> datetime:
    """MySQL DATETIME ve SQLite için UTC, timezone içermeyen değer üretir."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _iso_utc(value: datetime) -> str:
    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


class Repository:
    """MySQL üretim ve SQLite testleri için ortak SQLAlchemy repository katmanı."""

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
        self.initialize()

    @staticmethod
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    def initialize(self) -> None:
        metadata.create_all(self.engine)

    def close(self) -> None:
        self.engine.dispose()

    def ping(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(select(1))

    def get_cached_dns(self, domain: str) -> DNSResult | None:
        now = datetime.now(UTC).replace(tzinfo=None)
        statement = select(
            dns_cache.c.domain,
            dns_cache.c.state,
            dns_cache.c.detail,
        ).where(dns_cache.c.domain == domain, dns_cache.c.expires_at > now)
        with self.engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
        if row is None:
            return None
        return DNSResult(row["domain"], DNSState(row["state"]), row["detail"], True)

    def put_dns(self, result: DNSResult, checked_at: datetime, expires_at: datetime) -> None:
        values = {
            "domain": result.domain,
            "state": result.state.value,
            "detail": result.detail,
            "checked_at": _utc_naive(checked_at),
            "expires_at": _utc_naive(expires_at),
        }
        if self.engine.dialect.name == "mysql":
            statement = mysql_insert(dns_cache).values(**values)
            statement = statement.on_duplicate_key_update(
                state=statement.inserted.state,
                detail=statement.inserted.detail,
                checked_at=statement.inserted.checked_at,
                expires_at=statement.inserted.expires_at,
            )
        else:
            statement = sqlite_insert(dns_cache).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=[dns_cache.c.domain],
                set_={key: value for key, value in values.items() if key != "domain"},
            )
        with self.engine.begin() as connection:
            connection.execute(statement)

    def save_batch(
        self,
        batch_id: str,
        filename: str | None,
        summary: dict[str, Any],
        results: list[InternalResult],
    ) -> None:
        result_rows = []
        for item in results:
            source_for_hash = item.normalized or item.original
            result_rows.append(
                {
                    "batch_id": batch_id,
                    "row_number": item.row_number,
                    "email_hash": email_hash(source_for_hash),
                    "masked_email": mask_email(source_for_hash),
                    "domain": item.domain,
                    "status": item.status.value,
                    "reason_codes_json": [code.value for code in item.reason_codes],
                    "suggestion": mask_email(item.suggestion) if item.suggestion else None,
                }
            )
        with self.engine.begin() as connection:
            connection.execute(
                insert(batches).values(
                    id=batch_id,
                    filename=filename,
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                    summary_json=summary,
                )
            )
            if result_rows:
                connection.execute(insert(validation_results), result_rows)

    def get_batch(self, batch_id: str) -> dict[str, Any] | None:
        statement = select(
            batches.c.id,
            batches.c.filename,
            batches.c.created_at,
            batches.c.summary_json,
        ).where(batches.c.id == batch_id)
        with self.engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
        if row is None:
            return None
        return {
            "batch_id": row["id"],
            "filename": row["filename"],
            "created_at": _iso_utc(row["created_at"]),
            "summary": row["summary_json"],
        }

    def get_results(self, batch_id: str, offset: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        statement = (
            select(
                validation_results.c.row_number,
                validation_results.c.masked_email,
                validation_results.c.email_hash,
                validation_results.c.domain,
                validation_results.c.status,
                validation_results.c.reason_codes_json,
                validation_results.c.suggestion,
            )
            .where(validation_results.c.batch_id == batch_id)
            .order_by(validation_results.c.row_number)
            .limit(limit)
            .offset(offset)
        )
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [
            {
                "row_number": row["row_number"],
                "masked_email": row["masked_email"],
                "email_hash": row["email_hash"],
                "domain": row["domain"],
                "status": row["status"],
                "reason_codes": row["reason_codes_json"],
                "suggestion": row["suggestion"],
            }
            for row in rows
        ]

    def count_results_for_batches(self, batch_ids: list[str]) -> int:
        if not batch_ids:
            return 0
        statement = select(func.count()).select_from(validation_results).where(
            validation_results.c.batch_id.in_(batch_ids)
        )
        with self.engine.connect() as connection:
            return int(connection.scalar(statement) or 0)

    def delete_batches(self, batch_ids: list[str]) -> None:
        if not batch_ids:
            return
        with self.engine.begin() as connection:
            connection.execute(delete(batches).where(batches.c.id.in_(batch_ids)))

    def delete_dns_entries(self, domains: list[str]) -> None:
        if not domains:
            return
        with self.engine.begin() as connection:
            connection.execute(delete(dns_cache).where(dns_cache.c.domain.in_(domains)))
