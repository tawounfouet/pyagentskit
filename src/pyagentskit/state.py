"""Small coordination helpers for replaceable state stores."""

from __future__ import annotations

from .artifact_store import ArtifactRetentionPolicy, ArtifactStore
from .sessions import SessionStore

__all__ = ["SessionStateManager"]


class SessionStateManager:
    """Apply session deletion and its configured artifact-retention policy."""

    def __init__(
        self,
        session_store: SessionStore,
        *,
        artifact_store: ArtifactStore | None = None,
        artifact_policy: ArtifactRetentionPolicy | None = None,
    ) -> None:
        self.session_store = session_store
        self.artifact_store = artifact_store
        self.artifact_policy = artifact_policy or ArtifactRetentionPolicy()

    async def delete(self, session_id: str, *, tenant_id: str | None = None) -> bool:
        """Delete one tenant-scoped session and optionally cascade to its artifacts."""

        deleted = await self.session_store.delete(session_id, tenant_id=tenant_id)
        if deleted and self.artifact_store is not None and self.artifact_policy.delete_with_session:
            await self.artifact_store.delete_session(session_id, tenant_id=tenant_id)
        return deleted
