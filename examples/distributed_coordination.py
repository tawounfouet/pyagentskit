"""Offline lease and fencing-token example; no database or network required."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from pyagentskit.coordination import Lease, LeaseConflictError, MemoryLeaseStore


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 9, 9, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


class FencedResource:
    """Minimal illustration of rejecting a stale distributed worker."""

    def __init__(self) -> None:
        self.highest_token: dict[tuple[str | None, str], int] = {}

    def write(self, lease: Lease, value: str) -> str:
        key = (lease.tenant_id, lease.resource_id)
        highest = self.highest_token.get(key, 0)
        if lease.fencing_token < highest:
            raise LeaseConflictError("Stale fencing token")
        self.highest_token[key] = lease.fencing_token
        return value


async def main() -> None:
    clock = Clock()
    leases = MemoryLeaseStore(clock=clock)
    resource = FencedResource()
    first = await leases.acquire(
        "run:demo", owner_id="worker-a", tenant_id="tenant-a", ttl_seconds=5
    )
    resource.write(first, "first write")

    clock.now += timedelta(seconds=6)
    second = await leases.acquire(
        "run:demo", owner_id="worker-b", tenant_id="tenant-a", ttl_seconds=5
    )
    resource.write(second, "takeover write")
    try:
        resource.write(first, "late stale write")
    except LeaseConflictError:
        print(f"stale_rejected=True current_token={second.fencing_token}")


if __name__ == "__main__":
    asyncio.run(main())
