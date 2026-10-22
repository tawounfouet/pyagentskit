"""SQLite repositories for the remaining V2 P0 catalog aggregates."""

from __future__ import annotations

import sqlite3

from ...domain.entities import (
    Artifact,
    Conversation,
    ConversationMessage,
    RuntimeBinding,
    RuntimeInvocation,
    Session,
    Worker,
)
from ...domain.errors import ConcurrencyConflictError, DuplicateAggregateError
from ...domain.shared import (
    AggregateVersion,
    ArtifactId,
    ConversationId,
    MessageId,
    RuntimeBindingId,
    RuntimeInvocationId,
    SessionId,
    WorkerId,
)
from ._catalog_codec import (
    artifact_from_document,
    artifact_to_document,
    conversation_from_document,
    conversation_to_document,
    message_from_document,
    message_to_document,
    runtime_binding_from_document,
    runtime_binding_to_document,
    runtime_invocation_from_document,
    runtime_invocation_to_document,
    session_from_document,
    session_to_document,
    worker_from_document,
    worker_to_document,
)
from ._codec import dumps, loads
from .sqlite import _SQLiteDatabase, _SQLiteRepository


def _require_increment(
    new_version: AggregateVersion,
    expected_version: AggregateVersion,
) -> None:
    if new_version != expected_version.next():
        raise ConcurrencyConflictError(
            "saved aggregate version must advance by exactly one"
        )


class SQLiteSessionRepository(_SQLiteRepository):
    async def get(self, session_id: SessionId) -> Session | None:
        def operation() -> Session | None:
            row = self._db.connection.execute(
                "SELECT payload_json FROM v2_sessions WHERE id=?",
                (str(session_id),),
            ).fetchone()
            return (
                None
                if row is None
                else session_from_document(loads(row["payload_json"]))
            )

        return await self._db.call(operation)

    async def add(self, session: Session) -> None:
        def operation() -> None:
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_sessions("
                    "id, tenant_id, version, created_at, payload_json"
                    ") VALUES (?, ?, ?, ?, ?)",
                    (
                        str(session.id),
                        str(session.tenant_id),
                        session.version.value,
                        session.created_at.isoformat(),
                        dumps(session_to_document(session)),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateAggregateError(
                    f"session {session.id} already exists"
                ) from exc

        await self._db.call(operation)

    async def save(
        self,
        session: Session,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        _require_increment(session.version, expected_version)

        def operation() -> None:
            cursor = self._db.connection.execute(
                "UPDATE v2_sessions SET tenant_id=?, version=?, payload_json=? "
                "WHERE id=? AND version=?",
                (
                    str(session.tenant_id),
                    session.version.value,
                    dumps(session_to_document(session)),
                    str(session.id),
                    expected_version.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrencyConflictError(
                    f"stale or missing session {session.id}"
                )

        await self._db.call(operation)


class SQLiteConversationRepository(_SQLiteRepository):
    async def get(
        self,
        conversation_id: ConversationId,
    ) -> Conversation | None:
        def operation() -> Conversation | None:
            row = self._db.connection.execute(
                "SELECT payload_json FROM v2_conversations WHERE id=?",
                (str(conversation_id),),
            ).fetchone()
            return (
                None
                if row is None
                else conversation_from_document(loads(row["payload_json"]))
            )

        return await self._db.call(operation)

    async def add(self, conversation: Conversation) -> None:
        def operation() -> None:
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_conversations("
                    "id, session_id, version, created_at, payload_json"
                    ") VALUES (?, ?, ?, ?, ?)",
                    (
                        str(conversation.id),
                        str(conversation.session_id),
                        conversation.version.value,
                        conversation.created_at.isoformat(),
                        dumps(conversation_to_document(conversation)),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                existing = self._db.connection.execute(
                    "SELECT id FROM v2_conversations WHERE id=?",
                    (str(conversation.id),),
                ).fetchone()
                if existing is not None:
                    raise DuplicateAggregateError(
                        f"conversation {conversation.id} already exists"
                    ) from exc
                raise

        await self._db.call(operation)

    async def save(
        self,
        conversation: Conversation,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        _require_increment(conversation.version, expected_version)

        def operation() -> None:
            cursor = self._db.connection.execute(
                "UPDATE v2_conversations SET session_id=?, version=?, payload_json=? "
                "WHERE id=? AND version=?",
                (
                    str(conversation.session_id),
                    conversation.version.value,
                    dumps(conversation_to_document(conversation)),
                    str(conversation.id),
                    expected_version.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrencyConflictError(
                    f"stale or missing conversation {conversation.id}"
                )

        await self._db.call(operation)

    async def list_for_session(
        self,
        session_id: SessionId,
    ) -> tuple[Conversation, ...]:
        def operation() -> tuple[Conversation, ...]:
            rows = self._db.connection.execute(
                "SELECT payload_json FROM v2_conversations "
                "WHERE session_id=? ORDER BY created_at, id",
                (str(session_id),),
            ).fetchall()
            return tuple(
                conversation_from_document(loads(row["payload_json"]))
                for row in rows
            )

        return await self._db.call(operation)


class SQLiteMessageRepository(_SQLiteRepository):
    async def append(
        self,
        conversation_id: ConversationId,
        message: ConversationMessage,
    ) -> None:
        def operation() -> None:
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_messages("
                    "id, conversation_id, created_at, payload_json"
                    ") VALUES (?, ?, ?, ?)",
                    (
                        str(message.id),
                        str(conversation_id),
                        message.created_at.isoformat(),
                        dumps(message_to_document(message)),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                existing = self._db.connection.execute(
                    "SELECT id FROM v2_messages WHERE id=?",
                    (str(message.id),),
                ).fetchone()
                if existing is not None:
                    raise DuplicateAggregateError(
                        f"message {message.id} already exists"
                    ) from exc
                raise

        await self._db.call(operation)

    async def get(
        self,
        message_id: MessageId,
    ) -> ConversationMessage | None:
        def operation() -> ConversationMessage | None:
            row = self._db.connection.execute(
                "SELECT payload_json FROM v2_messages WHERE id=?",
                (str(message_id),),
            ).fetchone()
            return (
                None
                if row is None
                else message_from_document(loads(row["payload_json"]))
            )

        return await self._db.call(operation)

    async def list_for_conversation(
        self,
        conversation_id: ConversationId,
    ) -> tuple[ConversationMessage, ...]:
        def operation() -> tuple[ConversationMessage, ...]:
            rows = self._db.connection.execute(
                "SELECT payload_json FROM v2_messages "
                "WHERE conversation_id=? ORDER BY created_at, id",
                (str(conversation_id),),
            ).fetchall()
            return tuple(
                message_from_document(loads(row["payload_json"])) for row in rows
            )

        return await self._db.call(operation)


class SQLiteWorkerRepository(_SQLiteRepository):
    async def get(self, worker_id: WorkerId) -> Worker | None:
        def operation() -> Worker | None:
            row = self._db.connection.execute(
                "SELECT payload_json FROM v2_workers WHERE id=?",
                (str(worker_id),),
            ).fetchone()
            return (
                None
                if row is None
                else worker_from_document(loads(row["payload_json"]))
            )

        return await self._db.call(operation)

    async def add(self, worker: Worker) -> None:
        def operation() -> None:
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_workers("
                    "id, tenant_id, status, version, created_at, payload_json"
                    ") VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        str(worker.id),
                        str(worker.tenant_id),
                        worker.status.value,
                        worker.version.value,
                        worker.created_at.isoformat(),
                        dumps(worker_to_document(worker)),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateAggregateError(
                    f"worker {worker.id} already exists"
                ) from exc

        await self._db.call(operation)

    async def save(
        self,
        worker: Worker,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        _require_increment(worker.version, expected_version)

        def operation() -> None:
            cursor = self._db.connection.execute(
                "UPDATE v2_workers SET tenant_id=?, status=?, version=?, "
                "payload_json=? WHERE id=? AND version=?",
                (
                    str(worker.tenant_id),
                    worker.status.value,
                    worker.version.value,
                    dumps(worker_to_document(worker)),
                    str(worker.id),
                    expected_version.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrencyConflictError(
                    f"stale or missing worker {worker.id}"
                )

        await self._db.call(operation)


class SQLiteArtifactRepository(_SQLiteRepository):
    async def get(self, artifact_id: ArtifactId) -> Artifact | None:
        def operation() -> Artifact | None:
            row = self._db.connection.execute(
                "SELECT payload_json FROM v2_artifacts WHERE id=?",
                (str(artifact_id),),
            ).fetchone()
            return (
                None
                if row is None
                else artifact_from_document(loads(row["payload_json"]))
            )

        return await self._db.call(operation)

    async def add(self, artifact: Artifact) -> None:
        def operation() -> None:
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_artifacts(id, name, payload_json) "
                    "VALUES (?, ?, ?)",
                    (
                        str(artifact.id),
                        artifact.name,
                        dumps(artifact_to_document(artifact)),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateAggregateError(
                    f"artifact {artifact.id} already exists"
                ) from exc

        await self._db.call(operation)


class SQLiteRuntimeRepository(_SQLiteRepository):
    async def get_binding(
        self,
        binding_id: RuntimeBindingId,
    ) -> RuntimeBinding | None:
        def operation() -> RuntimeBinding | None:
            row = self._db.connection.execute(
                "SELECT payload_json FROM v2_runtime_bindings WHERE id=?",
                (str(binding_id),),
            ).fetchone()
            return (
                None
                if row is None
                else runtime_binding_from_document(loads(row["payload_json"]))
            )

        return await self._db.call(operation)

    async def add_binding(self, binding: RuntimeBinding) -> None:
        def operation() -> None:
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_runtime_bindings("
                    "id, run_id, runtime_id, runtime_family, bound_at, payload_json"
                    ") VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        str(binding.id),
                        None if binding.run_id is None else str(binding.run_id),
                        binding.resolved_runtime_id,
                        binding.runtime_family,
                        binding.bound_at.isoformat(),
                        dumps(runtime_binding_to_document(binding)),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                existing = self._db.connection.execute(
                    "SELECT id FROM v2_runtime_bindings WHERE id=?",
                    (str(binding.id),),
                ).fetchone()
                if existing is not None:
                    raise DuplicateAggregateError(
                        f"runtime binding {binding.id} already exists"
                    ) from exc
                raise

        await self._db.call(operation)

    async def get_invocation(
        self,
        invocation_id: RuntimeInvocationId,
    ) -> RuntimeInvocation | None:
        def operation() -> RuntimeInvocation | None:
            row = self._db.connection.execute(
                "SELECT payload_json FROM v2_runtime_invocations WHERE id=?",
                (str(invocation_id),),
            ).fetchone()
            return (
                None
                if row is None
                else runtime_invocation_from_document(loads(row["payload_json"]))
            )

        return await self._db.call(operation)

    async def add_invocation(self, invocation: RuntimeInvocation) -> None:
        def operation() -> None:
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_runtime_invocations("
                    "id, run_id, binding_id, status, version, payload_json"
                    ") VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        str(invocation.id),
                        str(invocation.run_id),
                        str(invocation.binding_id),
                        invocation.status.value,
                        invocation.version.value,
                        dumps(runtime_invocation_to_document(invocation)),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                existing = self._db.connection.execute(
                    "SELECT id FROM v2_runtime_invocations WHERE id=?",
                    (str(invocation.id),),
                ).fetchone()
                if existing is not None:
                    raise DuplicateAggregateError(
                        f"runtime invocation {invocation.id} already exists"
                    ) from exc
                raise

        await self._db.call(operation)

    async def save_invocation(
        self,
        invocation: RuntimeInvocation,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        _require_increment(invocation.version, expected_version)

        def operation() -> None:
            cursor = self._db.connection.execute(
                "UPDATE v2_runtime_invocations SET run_id=?, binding_id=?, status=?, "
                "version=?, payload_json=? WHERE id=? AND version=?",
                (
                    str(invocation.run_id),
                    str(invocation.binding_id),
                    invocation.status.value,
                    invocation.version.value,
                    dumps(runtime_invocation_to_document(invocation)),
                    str(invocation.id),
                    expected_version.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrencyConflictError(
                    f"stale or missing runtime invocation {invocation.id}"
                )

        await self._db.call(operation)


def bind_sqlite_catalog(database: _SQLiteDatabase) -> dict[str, object]:
    """Build catalog repositories over one existing SQLite transaction context."""

    return {
        "sessions": SQLiteSessionRepository(database),
        "conversations": SQLiteConversationRepository(database),
        "messages": SQLiteMessageRepository(database),
        "workers": SQLiteWorkerRepository(database),
        "runtimes": SQLiteRuntimeRepository(database),
        "artifacts": SQLiteArtifactRepository(database),
    }


__all__ = [
    "SQLiteArtifactRepository",
    "SQLiteConversationRepository",
    "SQLiteMessageRepository",
    "SQLiteRuntimeRepository",
    "SQLiteSessionRepository",
    "SQLiteWorkerRepository",
    "bind_sqlite_catalog",
]
