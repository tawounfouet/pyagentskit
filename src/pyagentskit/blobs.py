"""Provider-neutral object storage and artifact adapters.

SDK dependencies are optional and imported only by the explicit client factory
helpers. Applications may inject compatible clients for testing or custom
credential management.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import AsyncIterator, Callable, Mapping
from datetime import datetime
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from .artifact_store import ArtifactRecord, _record, _validate_id, _verify
from .exceptions import ArtifactIntegrityError, ArtifactNotFoundError, PersistenceError
from .runs import utc_now

__all__ = [
    "AzureBlobArtifactStore",
    "AzureBlobStore",
    "BlobStore",
    "ObjectArtifactStore",
    "S3ArtifactStore",
    "S3BlobStore",
    "create_azure_container_client",
    "create_s3_client",
]


@runtime_checkable
class BlobStore(Protocol):
    """Small asynchronous byte-object port with conditional creation."""

    async def put(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
        if_absent: bool = True,
    ) -> None: ...

    async def get(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> bool: ...

    def list_keys(self, *, prefix: str = "") -> AsyncIterator[str]: ...


def _key(value: str) -> str:
    if not value or value.startswith("/") or ".." in value.split("/"):
        raise PersistenceError("Invalid blob key")
    return value


def _error_code(exc: BaseException) -> str:
    response = getattr(exc, "response", None)
    if isinstance(response, Mapping):
        error = response.get("Error")
        if isinstance(error, Mapping):
            return str(error.get("Code", ""))
        return str(response.get("status_code", ""))
    return str(getattr(exc, "status_code", ""))


class S3BlobStore:
    """Async wrapper around an injected boto3-compatible S3 client."""

    def __init__(self, client: Any, *, bucket: str, prefix: str = "") -> None:
        if not bucket.strip():
            raise ValueError("S3 bucket cannot be blank")
        self.client = client
        self.bucket = bucket
        self.prefix = prefix.strip("/")

    def _remote(self, key: str) -> str:
        safe = _key(key)
        return f"{self.prefix}/{safe}" if self.prefix else safe

    async def put(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
        if_absent: bool = True,
    ) -> None:
        parameters: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": self._remote(key),
            "Body": bytes(data),
            "ContentType": content_type,
        }
        if if_absent:
            parameters["IfNoneMatch"] = "*"
        try:
            await asyncio.to_thread(self.client.put_object, **parameters)
        except Exception as exc:
            if _error_code(exc) in {"PreconditionFailed", "ConditionalRequestConflict", "412"}:
                raise PersistenceError("Blob already exists") from None
            raise PersistenceError("Cannot write S3 blob") from exc

    async def get(self, key: str) -> bytes:
        try:
            response = await asyncio.to_thread(
                self.client.get_object, Bucket=self.bucket, Key=self._remote(key)
            )
            body = response["Body"]
            value = await asyncio.to_thread(body.read)
            return bytes(value)
        except Exception as exc:
            if _error_code(exc) in {"NoSuchKey", "NotFound", "404"}:
                raise ArtifactNotFoundError("Blob not found") from None
            raise PersistenceError("Cannot read S3 blob") from exc

    async def delete(self, key: str) -> bool:
        remote = self._remote(key)
        try:
            await asyncio.to_thread(self.client.head_object, Bucket=self.bucket, Key=remote)
        except Exception as exc:
            if _error_code(exc) in {"NoSuchKey", "NotFound", "404"}:
                return False
            raise PersistenceError("Cannot inspect S3 blob") from exc
        try:
            await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=remote)
            return True
        except Exception as exc:
            raise PersistenceError("Cannot delete S3 blob") from exc

    async def list_keys(self, *, prefix: str = "") -> AsyncIterator[str]:
        remote_prefix = (
            self._remote(prefix) if prefix else (f"{self.prefix}/" if self.prefix else "")
        )
        continuation: str | None = None
        while True:
            parameters: dict[str, Any] = {"Bucket": self.bucket, "Prefix": remote_prefix}
            if continuation is not None:
                parameters["ContinuationToken"] = continuation
            try:
                response = await asyncio.to_thread(self.client.list_objects_v2, **parameters)
            except Exception as exc:
                raise PersistenceError("Cannot list S3 blobs") from exc
            for item in response.get("Contents", ()):
                remote = str(item["Key"])
                yield remote[len(self.prefix) + 1 :] if self.prefix else remote
            if not response.get("IsTruncated"):
                break
            continuation = str(response["NextContinuationToken"])


class AzureBlobStore:
    """Adapter around an injected async Azure ``ContainerClient``."""

    def __init__(self, container_client: Any, *, prefix: str = "") -> None:
        self.client = container_client
        self.prefix = prefix.strip("/")

    def _remote(self, key: str) -> str:
        safe = _key(key)
        return f"{self.prefix}/{safe}" if self.prefix else safe

    async def put(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
        if_absent: bool = True,
    ) -> None:
        try:
            try:
                from azure.storage.blob import ContentSettings  # type: ignore[import-not-found]

                settings: Any = ContentSettings(content_type=content_type)
            except ImportError:
                settings = {"content_type": content_type}
            await self.client.upload_blob(
                name=self._remote(key),
                data=bytes(data),
                overwrite=not if_absent,
                content_settings=settings,
            )
        except Exception as exc:
            if _error_code(exc) in {"BlobAlreadyExists", "ResourceExists", "409"}:
                raise PersistenceError("Blob already exists") from None
            raise PersistenceError("Cannot write Azure blob") from exc

    async def get(self, key: str) -> bytes:
        try:
            downloader = await self.client.download_blob(self._remote(key))
            return bytes(await downloader.readall())
        except Exception as exc:
            if _error_code(exc) in {"BlobNotFound", "ResourceNotFound", "404"}:
                raise ArtifactNotFoundError("Blob not found") from None
            raise PersistenceError("Cannot read Azure blob") from exc

    async def delete(self, key: str) -> bool:
        try:
            await self.client.delete_blob(self._remote(key))
            return True
        except Exception as exc:
            if _error_code(exc) in {"BlobNotFound", "ResourceNotFound", "404"}:
                return False
            raise PersistenceError("Cannot delete Azure blob") from exc

    async def list_keys(self, *, prefix: str = "") -> AsyncIterator[str]:
        remote_prefix = (
            self._remote(prefix) if prefix else (f"{self.prefix}/" if self.prefix else "")
        )
        try:
            iterator = self.client.list_blobs(name_starts_with=remote_prefix)
            async for item in iterator:
                remote = str(item.name)
                yield remote[len(self.prefix) + 1 :] if self.prefix else remote
        except Exception as exc:
            raise PersistenceError("Cannot list Azure blobs") from exc


def create_s3_client(**configuration: Any) -> Any:
    """Create a boto3 S3 client; credentials remain owned by the SDK chain."""

    try:
        import boto3  # type: ignore[import-not-found]
    except ImportError as exc:
        raise PersistenceError('S3 support requires pip install "pyagentskit[s3]"') from exc
    return boto3.client("s3", **configuration)


def create_azure_container_client(
    *, account_url: str, container_name: str, credential: Any = None
) -> Any:
    """Create an async Azure container client without retaining credentials."""

    if not account_url.strip() or not container_name.strip():
        raise ValueError("Azure account URL and container name cannot be blank")
    try:
        from azure.storage.blob.aio import ContainerClient  # type: ignore[import-not-found]
    except ImportError as exc:
        raise PersistenceError(
            'Azure Blob support requires pip install "pyagentskit[azure]"'
        ) from exc
    return ContainerClient(account_url, container_name, credential=credential)


class ObjectArtifactStore:
    """ArtifactStore backed by a BlobStore using integrity-checked sidecars."""

    def __init__(
        self,
        blobs: BlobStore,
        *,
        namespace: str = "artifacts",
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.blobs = blobs
        self.namespace = _key(namespace.strip("/"))
        self._clock = clock

    def _prefix(self, tenant_id: str | None) -> str:
        digest = hashlib.sha256((tenant_id or "").encode()).hexdigest()[:24]
        return f"{self.namespace}/{digest}"

    def _keys(self, artifact_id: str, tenant_id: str | None) -> tuple[str, str]:
        identifier = _validate_id(artifact_id)
        prefix = self._prefix(tenant_id)
        return f"{prefix}/{identifier}.blob", f"{prefix}/{identifier}.json"

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
        blob_key, metadata_key = self._keys(identifier, tenant_id)
        record = _record(
            artifact_id=identifier,
            data=data,
            name=name,
            media_type=media_type,
            uri=f"blob://{blob_key}",
            tenant_id=tenant_id,
            session_id=session_id,
            provenance=provenance,
            ttl_seconds=ttl_seconds,
            now=self._clock(),
        )
        await self.blobs.put(blob_key, data, content_type=media_type)
        try:
            await self.blobs.put(
                metadata_key,
                record.model_dump_json().encode(),
                content_type="application/json",
            )
        except Exception:
            await self.blobs.delete(blob_key)
            raise
        return record

    async def get(
        self, artifact_id: str, *, tenant_id: str | None = None
    ) -> tuple[ArtifactRecord, bytes]:
        blob_key, metadata_key = self._keys(artifact_id, tenant_id)
        try:
            metadata = await self.blobs.get(metadata_key)
            record = ArtifactRecord.model_validate_json(metadata)
        except ArtifactNotFoundError:
            raise ArtifactNotFoundError("Artifact not found") from None
        except ValueError:
            raise ArtifactIntegrityError("Artifact metadata is corrupted") from None
        if record.tenant_id != tenant_id or record.ref.artifact_id != artifact_id:
            raise ArtifactIntegrityError("Artifact metadata identity mismatch")
        data = await self.blobs.get(blob_key)
        _verify(record, data, self._clock())
        return record, data

    async def delete(self, artifact_id: str, *, tenant_id: str | None = None) -> bool:
        blob_key, metadata_key = self._keys(artifact_id, tenant_id)
        metadata_deleted = await self.blobs.delete(metadata_key)
        blob_deleted = await self.blobs.delete(blob_key)
        return metadata_deleted or blob_deleted

    async def delete_session(self, session_id: str, *, tenant_id: str | None = None) -> int:
        count = 0
        async for key in self.blobs.list_keys(prefix=self._prefix(tenant_id)):
            if not key.endswith(".json"):
                continue
            try:
                record = ArtifactRecord.model_validate_json(await self.blobs.get(key))
            except (ArtifactNotFoundError, ValueError):
                continue
            if record.tenant_id == tenant_id and record.session_id == session_id:
                count += int(await self.delete(record.ref.artifact_id, tenant_id=tenant_id))
        return count

    async def purge_expired(self, *, now: datetime | None = None) -> int:
        moment = now or self._clock()
        count = 0
        async for key in self.blobs.list_keys(prefix=self.namespace):
            if not key.endswith(".json"):
                continue
            try:
                record = ArtifactRecord.model_validate_json(await self.blobs.get(key))
            except (ArtifactNotFoundError, ValueError):
                continue
            if record.expires_at is not None and record.expires_at <= moment:
                count += int(await self.delete(record.ref.artifact_id, tenant_id=record.tenant_id))
        return count


class S3ArtifactStore(ObjectArtifactStore):
    """Convenience artifact adapter backed by S3."""

    def __init__(
        self,
        client: Any,
        *,
        bucket: str,
        prefix: str = "pyagentskit",
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        super().__init__(S3BlobStore(client, bucket=bucket, prefix=prefix), clock=clock)


class AzureBlobArtifactStore(ObjectArtifactStore):
    """Convenience artifact adapter backed by Azure Blob Storage."""

    def __init__(
        self,
        container_client: Any,
        *,
        prefix: str = "pyagentskit",
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        super().__init__(AzureBlobStore(container_client, prefix=prefix), clock=clock)
