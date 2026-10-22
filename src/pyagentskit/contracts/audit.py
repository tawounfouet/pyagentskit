"""Audit output port for V2 application services."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..domain.entities import AuditEvent


@runtime_checkable
class AuditSink(Protocol):
    async def append(self, event: AuditEvent) -> None: ...
