"""Explicit, resumable SQLite to PostgreSQL state migration."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from ._base import ContractModel
from .approvals import ApprovalRequest
from .exceptions import PersistenceError
from .memory import MemoryRecord
from .messages import Message
from .postgres import AsyncPostgresPool, PostgresRunStore
from .postgres_state import PostgresApprovalStore, PostgresMemoryStore, PostgresSessionStore
from .sessions import Session, SessionEntry

__all__ = ["StateMigrationReport", "migrate_sqlite_to_postgres"]


class StateMigrationReport(ContractModel):
    """Counts of validated source records processed by a migration."""

    source_files: int
    dry_run: bool
    sessions: int = 0
    session_entries: int = 0
    memories: int = 0
    approvals: int = 0
    durable_runs: int = 0


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def _session_documents(
    connection: sqlite3.Connection,
) -> Iterable[
    tuple[
        Session,
        tuple[SessionEntry, ...],
        dict[str, tuple[str, tuple[int, ...]]],
    ]
]:
    for row in connection.execute(
        "SELECT tenant_scope, session_id, agent_id, revision, created_at, updated_at, "
        "expires_at, metadata_json FROM sessions ORDER BY tenant_scope, session_id"
    ):
        tenant_id = str(row[0]) or None
        session = Session.model_validate(
            {
                "session_id": row[1],
                "agent_id": row[2],
                "tenant_id": tenant_id,
                "revision": row[3],
                "created_at": datetime.fromisoformat(row[4]),
                "updated_at": datetime.fromisoformat(row[5]),
                "expires_at": datetime.fromisoformat(row[6]) if row[6] else None,
                "metadata": json.loads(row[7]),
            }
        )
        entry_rows = connection.execute(
            "SELECT sequence, append_key, turn_id, message_json, created_at, run_id "
            "FROM session_entries WHERE tenant_scope=? AND session_id=? ORDER BY sequence",
            (row[0], row[1]),
        ).fetchall()
        entries = tuple(
            SessionEntry(
                session_id=session.session_id,
                tenant_id=tenant_id,
                sequence=int(item[0]),
                turn_id=str(item[2]),
                message=Message.model_validate_json(item[3]),
                created_at=datetime.fromisoformat(item[4]),
                run_id=UUID(item[5]) if item[5] else None,
            )
            for item in entry_rows
        )
        sequences: dict[str, list[int]] = {}
        for item in entry_rows:
            sequences.setdefault(str(item[1]), []).append(int(item[0]))
        fingerprints = {
            str(item[0]): str(item[1])
            for item in connection.execute(
                "SELECT idempotency_key, fingerprint FROM session_appends "
                "WHERE tenant_scope=? AND session_id=?",
                (row[0], row[1]),
            )
        }
        appends = {
            key: (fingerprint, tuple(sequences.get(key, ())))
            for key, fingerprint in fingerprints.items()
        }
        yield session, entries, appends


def _memories(connection: sqlite3.Connection) -> Iterable[MemoryRecord]:
    for row in connection.execute(
        "SELECT tenant_scope, agent_id, memory_id, session_id, content, tags_json, "
        "created_at, updated_at, expires_at, metadata_json FROM memories"
    ):
        yield MemoryRecord.model_validate(
            {
                "tenant_id": str(row[0]) or None,
                "agent_id": row[1],
                "memory_id": row[2],
                "session_id": row[3],
                "content": row[4],
                "tags": tuple(json.loads(row[5])),
                "created_at": datetime.fromisoformat(row[6]),
                "updated_at": datetime.fromisoformat(row[7]),
                "expires_at": datetime.fromisoformat(row[8]) if row[8] else None,
                "metadata": json.loads(row[9]),
            }
        )


async def migrate_sqlite_to_postgres(
    sources: Iterable[str | Path],
    pool: AsyncPostgresPool | None,
    *,
    table_prefix: str = "pyagentskit",
    dry_run: bool = False,
    overwrite: bool = False,
) -> StateMigrationReport:
    """Validate and migrate all recognized state tables from SQLite files.

    The operation is idempotent when the target contains identical data. It
    never replays effects: durable run aggregates are copied as documents.
    """

    paths = tuple(Path(item) for item in sources)
    if not paths:
        raise ValueError("At least one SQLite source is required")
    sessions: list[tuple[Session, tuple[SessionEntry, ...], dict[str, Any]]] = []
    memories: list[MemoryRecord] = []
    approvals: list[ApprovalRequest] = []
    runs: list[tuple[str, UUID, str]] = []
    for path in paths:
        if not path.is_file():
            raise PersistenceError(f"SQLite source does not exist: {path}")
        try:
            db_connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            try:
                tables = _tables(db_connection)
                if {"sessions", "session_entries", "session_appends"} <= tables:
                    sessions.extend(_session_documents(db_connection))
                if "memories" in tables:
                    memories.extend(_memories(db_connection))
                if "approvals" in tables:
                    approvals.extend(
                        ApprovalRequest.model_validate_json(row[0])
                        for row in db_connection.execute("SELECT payload_json FROM approvals")
                    )
                if "durable_runs" in tables:
                    runs.extend(
                        (str(row[0]), UUID(str(row[1])), str(row[2]))
                        for row in db_connection.execute(
                            "SELECT tenant_scope, run_id, payload_json FROM durable_runs"
                        )
                    )
            finally:
                db_connection.close()
        except (sqlite3.Error, ValueError) as exc:
            raise PersistenceError(f"Cannot validate SQLite source: {path}") from exc
    report = StateMigrationReport(
        source_files=len(paths),
        dry_run=dry_run,
        sessions=len(sessions),
        session_entries=sum(len(item[1]) for item in sessions),
        memories=len(memories),
        approvals=len(approvals),
        durable_runs=len(runs),
    )
    if dry_run:
        return report
    if pool is None:
        raise ValueError("A PostgreSQL pool is required unless dry_run is enabled")
    session_store = PostgresSessionStore(pool, table_prefix=table_prefix)
    memory_store = PostgresMemoryStore(pool, table_prefix=table_prefix)
    approval_store = PostgresApprovalStore(pool, table_prefix=table_prefix)
    run_store = PostgresRunStore(pool, table_prefix=table_prefix)
    await asyncio.gather(
        session_store.initialize(),
        memory_store.initialize(),
        approval_store.initialize(),
        run_store.initialize(),
    )
    for session, entries, appends in sessions:
        await session_store.import_document(session, entries, appends, overwrite=overwrite)
    for record in memories:
        await memory_store.upsert(record)
    for request in approvals:
        if overwrite:
            async with pool.acquire() as pg_connection, pg_connection.transaction():
                await approval_store._persist(pg_connection, request)
        else:
            await approval_store.create(request)
    for tenant_scope, run_id, payload in runs:
        await run_store.import_document(
            run_id,
            payload,
            tenant_id=tenant_scope or None,
            overwrite=overwrite,
        )
    return report
