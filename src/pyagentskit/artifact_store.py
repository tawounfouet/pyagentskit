"""Integrity-checked tenant-scoped artifact storage."""

from __future__ import annotations

import asyncio
import hashlib
import math
import re
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from pydantic import Field, field_validator

from ._base import ContractModel
from .artifacts import ArtifactRef
from .exceptions import ArtifactIntegrityError, ArtifactNotFoundError, PersistenceError
from .runs import utc_now
from .types import Identifier, NonEmptyString

__all__ = [
    "ArtifactRecord",
    "ArtifactRetentionPolicy",
    "ArtifactStore",
    "FileSystemArtifactStore",
    "MemoryArtifactStore",
]

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class ArtifactRetentionPolicy(ContractModel):
    """Inline threshold and default expiration for runtime-created artifacts."""

    inline_threshold_bytes: int = Field(default=65_536, ge=0)
    default_ttl_seconds: float | None = Field(default=None, gt=0)
    delete_with_session: bool = True

    @field_validator("default_ttl_seconds")
    @classmethod
    def validate_finite_ttl(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("artifact TTL must be finite")
        return value


class ArtifactRecord(ContractModel):
    """Stored artifact metadata; bytes remain outside serialized runtime state."""

    ref: ArtifactRef
    tenant_id: Identifier | None = None
    session_id: Identifier | None = None
    created_at: datetime
    expires_at: datetime | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at", "expires_at")
    @classmethod
    def validate_aware_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("artifact timestamps must be timezone-aware")
        return value


@runtime_checkable
class ArtifactStore(Protocol):
    """Replaceable byte store with integrity and tenant isolation."""

    async def put(
        self,
        data: bytes,
        *,
        name: str,
        media_type: str,
        tenant_id: str | None = None,
        session_id: str | None = None,
        provenance: dict[str, Any] | None = None,
        ttl_seconds: float | None = None,
        artifact_id: str | None = None,
    ) -> ArtifactRecord: ...

    async def get(
        self, artifact_id: str, *, tenant_id: str | None = None
    ) -> tuple[ArtifactRecord, bytes]: ...

    async def delete(self, artifact_id: str, *, tenant_id: str | None = None) -> bool: ...

    async def delete_session(self, session_id: str, *, tenant_id: str | None = None) -> int: ...

    async def purge_expired(self, *, now: datetime | None = None) -> int: ...


def _scope(tenant_id: str | None) -> str:
    return tenant_id or ""


def _validate_id(value: str) -> str:
    if not _SAFE_ID.fullmatch(value):
        raise PersistenceError("Invalid artifact identifier")
    return value


def _record(
    *,
    artifact_id: str,
    data: bytes,
    name: str,
    media_type: str,
    uri: str,
    tenant_id: str | None,
    session_id: str | None,
    provenance: dict[str, Any] | None,
    ttl_seconds: float | None,
    now: datetime,
) -> ArtifactRecord:
    if ttl_seconds is not None and (not math.isfinite(ttl_seconds) or ttl_seconds <= 0):
        raise PersistenceError("Artifact TTL must be finite and positive")
    checksum = "sha256:" + hashlib.sha256(data).hexdigest()
    return ArtifactRecord(
        ref=ArtifactRef(
            artifact_id=artifact_id,
            name=NonEmptyString(name),
            media_type=NonEmptyString(media_type),
            uri=NonEmptyString(uri),
            size_bytes=len(data),
            checksum=checksum,
        ),
        tenant_id=tenant_id,
        session_id=session_id,
        created_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds) if ttl_seconds is not None else None,
        provenance=dict(provenance or {}),
    )


def _verify(record: ArtifactRecord, data: bytes, now: datetime) -> None:
    if record.expires_at is not None and record.expires_at <= now:
        raise ArtifactNotFoundError("Artifact not found")
    if record.ref.size_bytes != len(data):
        raise ArtifactIntegrityError("Artifact size does not match metadata")
    checksum = "sha256:" + hashlib.sha256(data).hexdigest()
    if record.ref.checksum != checksum:
        raise ArtifactIntegrityError("Artifact checksum does not match metadata")


class MemoryArtifactStore:
    """Process-local artifact store for tests and ephemeral applications."""

    def __init__(self, *, clock: Callable[[], datetime] = utc_now) -> None:
        self._clock = clock
        self._items: dict[tuple[str, str], tuple[ArtifactRecord, bytes]] = {}
        self._lock = asyncio.Lock()

    async def put(
        self,
        data: bytes,
        *,
        name: str,
        media_type: str,
        tenant_id: str | None = None,
        session_id: str | None = None,
        provenance: dict[str, Any] | None = None,
        ttl_seconds: float | None = None,
        artifact_id: str | None = None,
    ) -> ArtifactRecord:
        identifier = _validate_id(artifact_id or uuid4().hex)
        record = _record(
            artifact_id=identifier,
            data=data,
            name=name,
            media_type=media_type,
            uri=f"artifact://{identifier}",
            tenant_id=tenant_id,
            session_id=session_id,
            provenance=provenance,
            ttl_seconds=ttl_seconds,
            now=self._clock(),
        )
        key = (_scope(tenant_id), identifier)
        async with self._lock:
            if key in self._items:
                raise PersistenceError("Artifact already exists")
            self._items[key] = (record, bytes(data))
        return record

    async def get(
        self, artifact_id: str, *, tenant_id: str | None = None
    ) -> tuple[ArtifactRecord, bytes]:
        key = (_scope(tenant_id), _validate_id(artifact_id))
        async with self._lock:
            item = self._items.get(key)
            if item is None:
                raise ArtifactNotFoundError("Artifact not found")
            record, data = item
            _verify(record, data, self._clock())
            return record, bytes(data)

    async def delete(self, artifact_id: str, *, tenant_id: str | None = None) -> bool:
        key = (_scope(tenant_id), _validate_id(artifact_id))
        async with self._lock:
            return self._items.pop(key, None) is not None

    async def delete_session(self, session_id: str, *, tenant_id: str | None = None) -> int:
        scope = _scope(tenant_id)
        async with self._lock:
            keys = [
                key
                for key, (record, _) in self._items.items()
                if key[0] == scope and record.session_id == session_id
            ]
            for key in keys:
                del self._items[key]
            return len(keys)

    async def purge_expired(self, *, now: datetime | None = None) -> int:
        moment = now or self._clock()
        async with self._lock:
            keys = [
                key
                for key, (record, _) in self._items.items()
                if record.expires_at is not None and record.expires_at <= moment
            ]
            for key in keys:
                del self._items[key]
            return len(keys)


class FileSystemArtifactStore:
    """Atomic local-filesystem store with sidecar metadata and checksum verification."""

    def __init__(self, root: str | Path, *, clock: Callable[[], datetime] = utc_now) -> None:
        self.root = Path(root).resolve()
        self._clock = clock
        self._lock = asyncio.Lock()
        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise PersistenceError("Cannot initialize artifact store") from exc

    def _directory(self, tenant_id: str | None) -> Path:
        digest = hashlib.sha256(_scope(tenant_id).encode()).hexdigest()[:24]
        return self.root / digest

    def _paths(self, artifact_id: str, tenant_id: str | None) -> tuple[Path, Path]:
        identifier = _validate_id(artifact_id)
        directory = self._directory(tenant_id)
        return directory / f"{identifier}.blob", directory / f"{identifier}.json"

    async def put(
        self,
        data: bytes,
        *,
        name: str,
        media_type: str,
        tenant_id: str | None = None,
        session_id: str | None = None,
        provenance: dict[str, Any] | None = None,
        ttl_seconds: float | None = None,
        artifact_id: str | None = None,
    ) -> ArtifactRecord:
        identifier = _validate_id(artifact_id or uuid4().hex)
        record = _record(
            artifact_id=identifier,
            data=data,
            name=name,
            media_type=media_type,
            uri=f"artifact://{identifier}",
            tenant_id=tenant_id,
            session_id=session_id,
            provenance=provenance,
            ttl_seconds=ttl_seconds,
            now=self._clock(),
        )
        async with self._lock:
            await asyncio.to_thread(self._put, record, data)
        return record

    def _put(self, record: ArtifactRecord, data: bytes) -> None:
        blob, metadata = self._paths(record.ref.artifact_id, record.tenant_id)
        blob.parent.mkdir(parents=True, exist_ok=True)
        if blob.exists() or metadata.exists():
            raise PersistenceError("Artifact already exists")
        blob_tmp = blob.with_suffix(".blob.tmp")
        metadata_tmp = metadata.with_suffix(".json.tmp")
        try:
            blob_tmp.write_bytes(data)
            metadata_tmp.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
            blob_tmp.replace(blob)
            metadata_tmp.replace(metadata)
        except OSError as exc:
            raise PersistenceError("Cannot persist artifact") from exc

    async def get(
        self, artifact_id: str, *, tenant_id: str | None = None
    ) -> tuple[ArtifactRecord, bytes]:
        async with self._lock:
            return await asyncio.to_thread(self._get, artifact_id, tenant_id)

    def _get(self, artifact_id: str, tenant_id: str | None) -> tuple[ArtifactRecord, bytes]:
        blob, metadata = self._paths(artifact_id, tenant_id)
        if not blob.is_file() or not metadata.is_file():
            raise ArtifactNotFoundError("Artifact not found")
        try:
            record = ArtifactRecord.model_validate_json(metadata.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ArtifactIntegrityError("Artifact metadata is corrupted") from None
        try:
            data = blob.read_bytes()
        except OSError as exc:
            raise PersistenceError("Cannot read artifact") from exc
        if record.tenant_id != tenant_id or record.ref.artifact_id != artifact_id:
            raise ArtifactIntegrityError("Artifact metadata identity mismatch")
        _verify(record, data, self._clock())
        return record, data

    async def delete(self, artifact_id: str, *, tenant_id: str | None = None) -> bool:
        async with self._lock:
            return await asyncio.to_thread(self._delete, artifact_id, tenant_id)

    def _delete(self, artifact_id: str, tenant_id: str | None) -> bool:
        blob, metadata = self._paths(artifact_id, tenant_id)
        existed = blob.exists() or metadata.exists()
        try:
            blob.unlink(missing_ok=True)
            metadata.unlink(missing_ok=True)
        except OSError as exc:
            raise PersistenceError("Cannot delete artifact") from exc
        return existed

    async def delete_session(self, session_id: str, *, tenant_id: str | None = None) -> int:
        async with self._lock:
            return await asyncio.to_thread(self._delete_session, session_id, tenant_id)

    def _delete_session(self, session_id: str, tenant_id: str | None) -> int:
        count = 0
        for metadata in self._directory(tenant_id).glob("*.json"):
            try:
                record = ArtifactRecord.model_validate_json(metadata.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if (
                record.tenant_id == tenant_id
                and record.session_id == session_id
                and self._delete(record.ref.artifact_id, tenant_id)
            ):
                count += 1
        return count

    async def purge_expired(self, *, now: datetime | None = None) -> int:
        moment = now or self._clock()
        async with self._lock:
            return await asyncio.to_thread(self._purge_expired, moment)

    def _purge_expired(self, now: datetime) -> int:
        count = 0
        for metadata in self.root.glob("*/*.json"):
            try:
                record = ArtifactRecord.model_validate_json(metadata.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if (
                record.expires_at is not None
                and record.expires_at <= now
                and self._delete(record.ref.artifact_id, record.tenant_id)
            ):
                count += 1
        return count
