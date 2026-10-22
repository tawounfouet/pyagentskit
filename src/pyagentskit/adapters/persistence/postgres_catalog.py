"""PostgreSQL repositories for the remaining V2 P0 catalog aggregates."""

from __future__ import annotations

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
from ...postgres import AsyncPostgresConnection, AsyncPostgresPool
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
from .postgres import _PostgresRepository, _PostgresV2Database


def _require_increment(
    new_version: AggregateVersion,
    expected_version: AggregateVersion,
) -> None:
    if new_version != expected_version.next():
        raise ConcurrencyConflictError(
            "saved aggregate version must advance by exactly one"
        )


class PostgresV2SessionRepository(_PostgresRepository):
    async def get(self, session_id: SessionId) -> Session | None:
        table = self._db.table("sessions")

        async def operation(connection: AsyncPostgresConnection) -> Session | None:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} WHERE id=$1",
                str(session_id),
            )
            return (
                None
                if row is None
                else session_from_document(loads(str(row["payload_json"])))
            )

        return await self._db.call(operation)

    async def add(self, session: Session) -> None:
        table = self._db.table("sessions")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"INSERT INTO {table}("
                "id,tenant_id,version,created_at,payload_json"
                ") VALUES ($1,$2,$3,$4,$5::jsonb) "
                "ON CONFLICT(id) DO NOTHING RETURNING id",
                str(session.id),
                str(session.tenant_id),
                session.version.value,
                session.created_at,
                dumps(session_to_document(session)),
            )
            if row is None:
                raise DuplicateAggregateError(
                    f"session {session.id} already exists"
                )

        await self._db.call(operation)

    async def save(
        self,
        session: Session,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        _require_increment(session.version, expected_version)
        table = self._db.table("sessions")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET tenant_id=$2,version=$3,payload_json=$4::jsonb "
                "WHERE id=$1 AND version=$5 RETURNING id",
                str(session.id),
                str(session.tenant_id),
                session.version.value,
                dumps(session_to_document(session)),
                expected_version.value,
            )
            if row is None:
                raise ConcurrencyConflictError(
                    f"stale or missing session {session.id}"
                )

        await self._db.call(operation)


class PostgresV2ConversationRepository(_PostgresRepository):
    async def get(
        self,
        conversation_id: ConversationId,
    ) -> Conversation | None:
        table = self._db.table("conversations")

        async def operation(
            connection: AsyncPostgresConnection,
        ) -> Conversation | None:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} WHERE id=$1",
                str(conversation_id),
            )
            return (
                None
                if row is None
                else conversation_from_document(loads(str(row["payload_json"])))
            )

        return await self._db.call(operation)

    async def add(self, conversation: Conversation) -> None:
        table = self._db.table("conversations")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"INSERT INTO {table}("
                "id,session_id,version,created_at,payload_json"
                ") VALUES ($1,$2,$3,$4,$5::jsonb) "
                "ON CONFLICT(id) DO NOTHING RETURNING id",
                str(conversation.id),
                str(conversation.session_id),
                conversation.version.value,
                conversation.created_at,
                dumps(conversation_to_document(conversation)),
            )
            if row is not None:
                return
            duplicate = await connection.fetchrow(
                f"SELECT id FROM {table} WHERE id=$1",
                str(conversation.id),
            )
            if duplicate is not None:
                raise DuplicateAggregateError(
                    f"conversation {conversation.id} already exists"
                )
            raise ConcurrencyConflictError(
                f"conversation parent session {conversation.session_id} is unavailable"
            )

        await self._db.call(operation)

    async def save(
        self,
        conversation: Conversation,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        _require_increment(conversation.version, expected_version)
        table = self._db.table("conversations")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET session_id=$2,version=$3,payload_json=$4::jsonb "
                "WHERE id=$1 AND version=$5 RETURNING id",
                str(conversation.id),
                str(conversation.session_id),
                conversation.version.value,
                dumps(conversation_to_document(conversation)),
                expected_version.value,
            )
            if row is None:
                raise ConcurrencyConflictError(
                    f"stale or missing conversation {conversation.id}"
                )

        await self._db.call(operation)

    async def list_for_session(
        self,
        session_id: SessionId,
    ) -> tuple[Conversation, ...]:
        table = self._db.table("conversations")

        async def operation(
            connection: AsyncPostgresConnection,
        ) -> tuple[Conversation, ...]:
            rows = await connection.fetch(
                f"SELECT payload_json FROM {table} "
                "WHERE session_id=$1 ORDER BY created_at,id",
                str(session_id),
            )
            return tuple(
                conversation_from_document(loads(str(row["payload_json"])))
                for row in rows
            )

        return await self._db.call(operation)


class PostgresV2MessageRepository(_PostgresRepository):
    async def append(
        self,
        conversation_id: ConversationId,
        message: ConversationMessage,
    ) -> None:
        table = self._db.table("messages")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"INSERT INTO {table}("
                "id,conversation_id,created_at,payload_json"
                ") VALUES ($1,$2,$3,$4::jsonb) "
                "ON CONFLICT(id) DO NOTHING RETURNING id",
                str(message.id),
                str(conversation_id),
                message.created_at,
                dumps(message_to_document(message)),
            )
            if row is not None:
                return
            duplicate = await connection.fetchrow(
                f"SELECT id FROM {table} WHERE id=$1",
                str(message.id),
            )
            if duplicate is not None:
                raise DuplicateAggregateError(
                    f"message {message.id} already exists"
                )
            raise ConcurrencyConflictError(
                f"message parent conversation {conversation_id} is unavailable"
            )

        await self._db.call(operation)

    async def get(
        self,
        message_id: MessageId,
    ) -> ConversationMessage | None:
        table = self._db.table("messages")

        async def operation(
            connection: AsyncPostgresConnection,
        ) -> ConversationMessage | None:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} WHERE id=$1",
                str(message_id),
            )
            return (
                None
                if row is None
                else message_from_document(loads(str(row["payload_json"])))
            )

        return await self._db.call(operation)

    async def list_for_conversation(
        self,
        conversation_id: ConversationId,
    ) -> tuple[ConversationMessage, ...]:
        table = self._db.table("messages")

        async def operation(
            connection: AsyncPostgresConnection,
        ) -> tuple[ConversationMessage, ...]:
            rows = await connection.fetch(
                f"SELECT payload_json FROM {table} "
                "WHERE conversation_id=$1 ORDER BY created_at,id",
                str(conversation_id),
            )
            return tuple(
                message_from_document(loads(str(row["payload_json"]))) for row in rows
            )

        return await self._db.call(operation)


class PostgresV2WorkerRepository(_PostgresRepository):
    async def get(self, worker_id: WorkerId) -> Worker | None:
        table = self._db.table("workers")

        async def operation(connection: AsyncPostgresConnection) -> Worker | None:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} WHERE id=$1",
                str(worker_id),
            )
            return (
                None
                if row is None
                else worker_from_document(loads(str(row["payload_json"])))
            )

        return await self._db.call(operation)

    async def add(self, worker: Worker) -> None:
        table = self._db.table("workers")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"INSERT INTO {table}("
                "id,tenant_id,status,version,created_at,payload_json"
                ") VALUES ($1,$2,$3,$4,$5,$6::jsonb) "
                "ON CONFLICT(id) DO NOTHING RETURNING id",
                str(worker.id),
                str(worker.tenant_id),
                worker.status.value,
                worker.version.value,
                worker.created_at,
                dumps(worker_to_document(worker)),
            )
            if row is None:
                raise DuplicateAggregateError(
                    f"worker {worker.id} already exists"
                )

        await self._db.call(operation)

    async def save(
        self,
        worker: Worker,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        _require_increment(worker.version, expected_version)
        table = self._db.table("workers")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET tenant_id=$2,status=$3,version=$4,"
                "payload_json=$5::jsonb WHERE id=$1 AND version=$6 RETURNING id",
                str(worker.id),
                str(worker.tenant_id),
                worker.status.value,
                worker.version.value,
                dumps(worker_to_document(worker)),
                expected_version.value,
            )
            if row is None:
                raise ConcurrencyConflictError(
                    f"stale or missing worker {worker.id}"
                )

        await self._db.call(operation)


class PostgresV2ArtifactRepository(_PostgresRepository):
    async def get(self, artifact_id: ArtifactId) -> Artifact | None:
        table = self._db.table("artifacts")

        async def operation(connection: AsyncPostgresConnection) -> Artifact | None:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} WHERE id=$1",
                str(artifact_id),
            )
            return (
                None
                if row is None
                else artifact_from_document(loads(str(row["payload_json"])))
            )

        return await self._db.call(operation)

    async def add(self, artifact: Artifact) -> None:
        table = self._db.table("artifacts")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"INSERT INTO {table}(id,name,payload_json) "
                "VALUES ($1,$2,$3::jsonb) "
                "ON CONFLICT(id) DO NOTHING RETURNING id",
                str(artifact.id),
                artifact.name,
                dumps(artifact_to_document(artifact)),
            )
            if row is None:
                raise DuplicateAggregateError(
                    f"artifact {artifact.id} already exists"
                )

        await self._db.call(operation)


class PostgresV2RuntimeRepository(_PostgresRepository):
    async def get_binding(
        self,
        binding_id: RuntimeBindingId,
    ) -> RuntimeBinding | None:
        table = self._db.table("runtime_bindings")

        async def operation(
            connection: AsyncPostgresConnection,
        ) -> RuntimeBinding | None:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} WHERE id=$1",
                str(binding_id),
            )
            return (
                None
                if row is None
                else runtime_binding_from_document(loads(str(row["payload_json"])))
            )

        return await self._db.call(operation)

    async def add_binding(self, binding: RuntimeBinding) -> None:
        table = self._db.table("runtime_bindings")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"INSERT INTO {table}("
                "id,run_id,runtime_id,runtime_family,bound_at,payload_json"
                ") VALUES ($1,$2,$3,$4,$5,$6::jsonb) "
                "ON CONFLICT(id) DO NOTHING RETURNING id",
                str(binding.id),
                None if binding.run_id is None else str(binding.run_id),
                binding.resolved_runtime_id,
                binding.runtime_family,
                binding.bound_at,
                dumps(runtime_binding_to_document(binding)),
            )
            if row is not None:
                return
            duplicate = await connection.fetchrow(
                f"SELECT id FROM {table} WHERE id=$1",
                str(binding.id),
            )
            if duplicate is not None:
                raise DuplicateAggregateError(
                    f"runtime binding {binding.id} already exists"
                )
            raise ConcurrencyConflictError(
                "runtime binding references unavailable durable state"
            )

        await self._db.call(operation)

    async def get_invocation(
        self,
        invocation_id: RuntimeInvocationId,
    ) -> RuntimeInvocation | None:
        table = self._db.table("runtime_invocations")

        async def operation(
            connection: AsyncPostgresConnection,
        ) -> RuntimeInvocation | None:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} WHERE id=$1",
                str(invocation_id),
            )
            return (
                None
                if row is None
                else runtime_invocation_from_document(loads(str(row["payload_json"])))
            )

        return await self._db.call(operation)

    async def add_invocation(self, invocation: RuntimeInvocation) -> None:
        table = self._db.table("runtime_invocations")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"INSERT INTO {table}("
                "id,run_id,binding_id,status,version,payload_json"
                ") VALUES ($1,$2,$3,$4,$5,$6::jsonb) "
                "ON CONFLICT(id) DO NOTHING RETURNING id",
                str(invocation.id),
                str(invocation.run_id),
                str(invocation.binding_id),
                invocation.status.value,
                invocation.version.value,
                dumps(runtime_invocation_to_document(invocation)),
            )
            if row is not None:
                return
            duplicate = await connection.fetchrow(
                f"SELECT id FROM {table} WHERE id=$1",
                str(invocation.id),
            )
            if duplicate is not None:
                raise DuplicateAggregateError(
                    f"runtime invocation {invocation.id} already exists"
                )
            raise ConcurrencyConflictError(
                "runtime invocation references unavailable durable state"
            )

        await self._db.call(operation)

    async def save_invocation(
        self,
        invocation: RuntimeInvocation,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        _require_increment(invocation.version, expected_version)
        table = self._db.table("runtime_invocations")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET run_id=$2,binding_id=$3,status=$4,"
                "version=$5,payload_json=$6::jsonb "
                "WHERE id=$1 AND version=$7 RETURNING id",
                str(invocation.id),
                str(invocation.run_id),
                str(invocation.binding_id),
                invocation.status.value,
                invocation.version.value,
                dumps(runtime_invocation_to_document(invocation)),
                expected_version.value,
            )
            if row is None:
                raise ConcurrencyConflictError(
                    f"stale or missing runtime invocation {invocation.id}"
                )

        await self._db.call(operation)


def bind_postgres_catalog(
    database: _PostgresV2Database,
) -> dict[str, object]:
    """Build catalog repositories over one existing PostgreSQL transaction context."""

    return {
        "sessions": PostgresV2SessionRepository(database),
        "conversations": PostgresV2ConversationRepository(database),
        "messages": PostgresV2MessageRepository(database),
        "workers": PostgresV2WorkerRepository(database),
        "runtimes": PostgresV2RuntimeRepository(database),
        "artifacts": PostgresV2ArtifactRepository(database),
    }


def make_postgres_catalog(
    pool: AsyncPostgresPool,
    *,
    table_prefix: str = "pyagentskit",
) -> dict[str, object]:
    database = _PostgresV2Database(pool, table_prefix=table_prefix)
    return bind_postgres_catalog(database)


__all__ = [
    "PostgresV2ArtifactRepository",
    "PostgresV2ConversationRepository",
    "PostgresV2MessageRepository",
    "PostgresV2RuntimeRepository",
    "PostgresV2SessionRepository",
    "PostgresV2WorkerRepository",
    "bind_postgres_catalog",
    "make_postgres_catalog",
]
