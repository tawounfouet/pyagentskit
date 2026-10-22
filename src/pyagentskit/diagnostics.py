"""Dependency-free installation and configuration diagnostics."""

from __future__ import annotations

import importlib.util
import platform
import sys
from enum import StrEnum
from typing import Any

from pydantic import Field

from ._base import ContractModel
from ._version import __version__

__all__ = ["DoctorCheck", "DoctorReport", "DoctorStatus", "run_doctor"]


class DoctorStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class DoctorCheck(ContractModel):
    name: str = Field(min_length=1)
    status: DoctorStatus
    message: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DoctorReport(ContractModel):
    version: str
    healthy: bool
    checks: tuple[DoctorCheck, ...]


def run_doctor() -> DoctorReport:
    """Inspect local runtime compatibility without network or credentials."""

    supported = (3, 11) <= sys.version_info[:2] < (3, 15)
    checks = [
        DoctorCheck(
            name="python",
            status=DoctorStatus.PASS if supported else DoctorStatus.FAIL,
            message=(
                f"Python {platform.python_version()} is supported"
                if supported
                else f"Python {platform.python_version()} is outside 3.11-3.14"
            ),
        ),
        DoctorCheck(
            name="pydantic",
            status=(
                DoctorStatus.PASS
                if importlib.util.find_spec("pydantic") is not None
                else DoctorStatus.FAIL
            ),
            message="Core dependency is importable",
        ),
    ]
    for module, extra in (
        ("httpx", "providers"),
        ("opentelemetry", "opentelemetry"),
        ("asyncpg", "postgres"),
    ):
        present = importlib.util.find_spec(module) is not None
        checks.append(
            DoctorCheck(
                name=f"extra.{extra}",
                status=DoctorStatus.PASS if present else DoctorStatus.WARN,
                message=(
                    f"Optional {extra} support is available"
                    if present
                    else f"Install [{extra}] to enable it"
                ),
            )
        )
    return DoctorReport(
        version=__version__,
        healthy=all(item.status is not DoctorStatus.FAIL for item in checks),
        checks=tuple(checks),
    )
