import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.models import DNSResult, DNSState, InternalResult
from app.privacy import email_hash, mask_email


class Repository:
    def __init__(self, database_path: Path | str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS dns_cache (
                    domain TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    detail TEXT,
                    checked_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS batches (
                    id TEXT PRIMARY KEY,
                    filename TEXT,
                    created_at TEXT NOT NULL,
                    summary_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS validation_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL,
                    row_number INTEGER NOT NULL,
                    email_hash TEXT NOT NULL,
                    masked_email TEXT NOT NULL,
                    domain TEXT,
                    status TEXT NOT NULL,
                    reason_codes_json TEXT NOT NULL,
                    suggestion TEXT,
                    FOREIGN KEY(batch_id) REFERENCES batches(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_results_batch
                    ON validation_results(batch_id, row_number);
                """
            )

    def get_cached_dns(self, domain: str) -> DNSResult | None:
        now = datetime.now(UTC).isoformat()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT domain, state, detail FROM dns_cache WHERE domain = ? AND expires_at > ?",
                (domain, now),
            ).fetchone()
        if not row:
            return None
        return DNSResult(row["domain"], DNSState(row["state"]), row["detail"], True)

    def put_dns(self, result: DNSResult, checked_at: datetime, expires_at: datetime) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO dns_cache(domain, state, detail, checked_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(domain) DO UPDATE SET
                    state = excluded.state,
                    detail = excluded.detail,
                    checked_at = excluded.checked_at,
                    expires_at = excluded.expires_at
                """,
                (
                    result.domain,
                    result.state.value,
                    result.detail,
                    checked_at.isoformat(),
                    expires_at.isoformat(),
                ),
            )

    def save_batch(
        self,
        batch_id: str,
        filename: str | None,
        summary: dict[str, Any],
        results: list[InternalResult],
    ) -> None:
        created_at = datetime.now(UTC).isoformat()
        rows = []
        for item in results:
            source_for_hash = item.normalized or item.original
            rows.append(
                (
                    batch_id,
                    item.row_number,
                    email_hash(source_for_hash),
                    mask_email(item.normalized or item.original),
                    item.domain,
                    item.status.value,
                    json.dumps([code.value for code in item.reason_codes]),
                    mask_email(item.suggestion) if item.suggestion else None,
                )
            )
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO batches(id, filename, created_at, summary_json) VALUES (?, ?, ?, ?)",
                (batch_id, filename, created_at, json.dumps(summary, ensure_ascii=False)),
            )
            connection.executemany(
                """
                INSERT INTO validation_results(
                    batch_id, row_number, email_hash, masked_email, domain,
                    status, reason_codes_json, suggestion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def get_batch(self, batch_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id, filename, created_at, summary_json FROM batches WHERE id = ?",
                (batch_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "batch_id": row["id"],
            "filename": row["filename"],
            "created_at": row["created_at"],
            "summary": json.loads(row["summary_json"]),
        }

    def get_results(self, batch_id: str, offset: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT row_number, masked_email, email_hash, domain, status,
                       reason_codes_json, suggestion
                FROM validation_results
                WHERE batch_id = ?
                ORDER BY row_number
                LIMIT ? OFFSET ?
                """,
                (batch_id, limit, offset),
            ).fetchall()
        return [
            {
                "row_number": row["row_number"],
                "masked_email": row["masked_email"],
                "email_hash": row["email_hash"],
                "domain": row["domain"],
                "status": row["status"],
                "reason_codes": json.loads(row["reason_codes_json"]),
                "suggestion": row["suggestion"],
            }
            for row in rows
        ]

