"""Run the complete reproducible PyAgentsKit release qualification."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "release-dist"
EXPECTED_VERSION = "1.6.0"
REQUIRED_SDIST_FILES = {
    "README.md",
    "STABLE_RELEASE_NOTES.md",
    "PROVIDER_QUALIFICATION.md",
    "AUDIT_RC2.md",
    "CHECK_RESULTS.md",
    "OPENROUTER_ALPHA1_RELEASE_NOTES.md",
    "OPENROUTER_BETA1_RELEASE_NOTES.md",
    "OPENROUTER_QUALIFICATION.md",
    "OPENROUTER_ADVANCED_QUALIFICATION.md",
    "OPENROUTER_RC1_RELEASE_NOTES.md",
    "OPENROUTER_RC1_QUALIFICATION.md",
    "AUDIT_OPENROUTER_BETA1.md",
    "OPENROUTER_STABLE_RELEASE_NOTES.md",
    "OPENROUTER_COMPATIBILITY_MATRIX.md",
    "OPENROUTER_API_STABILITY.md",
    "AUDIT_OPENROUTER_RC1.md",
    "LOT_08_RELEASE_NOTES.md",
    "LOT_08_QUALIFICATION.md",
    "LOT_08_API_STABILITY.md",
    "AUDIT_LOT_08.md",
    "LOT_09_RELEASE_NOTES.md",
    "LOT_09_QUALIFICATION.md",
    "LOT_09_API_STABILITY.md",
    "AUDIT_LOT_09.md",
    "LOT_10_RELEASE_NOTES.md",
    "LOT_10_QUALIFICATION.md",
    "LOT_10_API_STABILITY.md",
    "AUDIT_LOT_10.md",
    "LOT_11_RELEASE_NOTES.md",
    "LOT_11_QUALIFICATION.md",
    "LOT_11_API_STABILITY.md",
    "AUDIT_LOT_11.md",
    "BENCHMARK_RESULTS.md",
    "MIGRATION_TO_V1.md",
    "DEPRECATION_POLICY.md",
    "V1_RELEASE_NOTES.md",
    "V1_QUALIFICATION.md",
    "V1_API_STABILITY.md",
    "V1_COMPATIBILITY_MATRIX.md",
    "V1_SECURITY_AUDIT.md",
    "AUDIT_V1.md",
    "V1_1_RELEASE_NOTES.md",
    "V1_1_QUALIFICATION.md",
    "V1_1_API_COMPATIBILITY.md",
    "AUDIT_V1_1.md",
    "02_PYAGENTSKIT_POST_V1_ROADMAP.md",
    "V1_2_RELEASE_NOTES.md",
    "V1_2_QUALIFICATION.md",
    "V1_2_API_COMPATIBILITY.md",
    "AUDIT_V1_2.md",
    "V1_3_RELEASE_NOTES.md",
    "V1_3_QUALIFICATION.md",
    "V1_3_API_COMPATIBILITY.md",
    "V1_3_STORE_COMPATIBILITY.md",
    "AUDIT_V1_3.md",
    "V1_4_RELEASE_NOTES.md",
    "V1_4_QUALIFICATION.md",
    "V1_4_API_COMPATIBILITY.md",
    "V1_4_STORE_COMPATIBILITY.md",
    "AUDIT_V1_4.md",
    "V1_5_RELEASE_NOTES.md",
    "V1_5_QUALIFICATION.md",
    "V1_5_API_COMPATIBILITY.md",
    "V1_5_DISTRIBUTED_EXECUTION_MATRIX.md",
    "AUDIT_V1_5.md",
    "V1_6_RELEASE_NOTES.md",
    "V1_6_QUALIFICATION.md",
    "V1_6_API_COMPATIBILITY.md",
    "V1_6_OPERATIONS_MATRIX.md",
    "AUDIT_V1_6.md",
}


def run(*command: str, cwd: Path = ROOT) -> None:
    """Execute one release command and fail on any non-zero exit."""
    print("+", " ".join(command), flush=True)
    environment = os.environ.copy()
    environment["PIP_NO_INDEX"] = "1"
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    environment["SOURCE_DATE_EPOCH"] = "1788739200"
    subprocess.run(command, cwd=cwd, check=True, env=environment)


def verify_versions() -> None:
    """Require one consistent public and packaging version."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    if project["version"] != EXPECTED_VERSION:
        raise RuntimeError(f"pyproject version is {project['version']!r}")
    run(
        sys.executable,
        "-c",
        (
            "import pyagentskit; "
            f"assert pyagentskit.__version__ == {EXPECTED_VERSION!r}, pyagentskit.__version__"
        ),
    )


def verify_secret_hygiene() -> None:
    """Reject a project-level .env while allowing the committed empty example."""
    if (ROOT / ".env").exists():
        raise RuntimeError("project .env must not be included in a release")


def build_distributions() -> tuple[Path, Path]:
    """Build fresh distributions into a release-only directory."""
    if DIST.exists():
        shutil.rmtree(DIST)
    run(sys.executable, "-m", "build", "--no-isolation", "--outdir", str(DIST))
    wheels = list(DIST.glob(f"pyagentskit-{EXPECTED_VERSION}-*.whl"))
    sdists = list(DIST.glob(f"pyagentskit-{EXPECTED_VERSION}.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise RuntimeError(f"unexpected distributions: wheels={wheels}, sdists={sdists}")
    return wheels[0], sdists[0]


def verify_archives(wheel: Path, sdist: Path) -> None:
    """Check stable metadata, required evidence and archive hygiene."""
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith("METADATA"))
        metadata = archive.read(metadata_name).decode("utf-8")
        if f"Version: {EXPECTED_VERSION}\n" not in metadata:
            raise RuntimeError("wheel metadata version mismatch")

    with tarfile.open(sdist, "r:gz") as archive:
        names = archive.getnames()
        prefix = f"pyagentskit-{EXPECTED_VERSION}/"
        missing = {name for name in REQUIRED_SDIST_FILES if prefix + name not in names}
        if missing:
            raise RuntimeError(f"sdist evidence missing: {sorted(missing)}")
        forbidden = {
            ".venv",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "__pycache__",
            ".coverage",
            ".env",
        }
        contaminated = [
            name for name in names if any(part in forbidden for part in Path(name).parts)
        ]
        if contaminated:
            raise RuntimeError(f"sdist contains forbidden paths: {contaminated[:5]}")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_reproducible_build(wheel: Path, sdist: Path) -> None:
    """Build twice under a fixed epoch and require byte-identical artifacts."""
    with tempfile.TemporaryDirectory(prefix="pyagentskit-rebuild-") as temporary:
        rebuilt = Path(temporary)
        run(sys.executable, "-m", "build", "--no-isolation", "--outdir", str(rebuilt))
        other_wheel = next(rebuilt.glob(f"pyagentskit-{EXPECTED_VERSION}-*.whl"))
        other_sdist = next(rebuilt.glob(f"pyagentskit-{EXPECTED_VERSION}.tar.gz"))
        if digest(wheel) != digest(other_wheel) or digest(sdist) != digest(other_sdist):
            raise RuntimeError("distributions are not reproducible under SOURCE_DATE_EPOCH")


def smoke_install(wheel: Path) -> None:
    """Install the wheel away from the source and run an offline agent cycle."""
    with tempfile.TemporaryDirectory(prefix="pyagentskit-release-") as temporary:
        target = Path(temporary)
        virtualenv = target / "venv"
        run(sys.executable, "-m", "venv", "--system-site-packages", str(virtualenv), cwd=target)
        python = virtualenv / "bin" / "python"
        if sys.platform == "win32":
            python = virtualenv / "Scripts" / "python.exe"
        run(
            str(python),
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--force-reinstall",
            str(wheel),
            cwd=target,
        )
        probe = (
            "import pathlib, pyagentskit; "
            f"assert pyagentskit.__version__ == {EXPECTED_VERSION!r}; "
            "assert 'site-packages' in str(pathlib.Path(pyagentskit.__file__).resolve()); "
            "from pyagentskit.providers.openrouter import OpenRouterModel; "
            "from pyagentskit.providers.openrouter_catalog import OpenRouterCatalog; "
            "from pyagentskit.providers.openrouter_routing import OpenRouterRoutingPolicy; "
            "assert OpenRouterModel.provider == 'openrouter'; "
            "assert OpenRouterCatalog.endpoint.endswith('/api/v1'); "
            "assert OpenRouterRoutingPolicy().require_parameters is True; "
            "from pyagentskit import (GuardrailPipeline, MemoryApprovalStore, "
            "MemorySessionStore, WindowContextPolicy); "
            "assert GuardrailPipeline and MemoryApprovalStore; "
            "assert MemorySessionStore and WindowContextPolicy"
            "; from pyagentskit import DurableRunner, MemoryRunStore, SQLiteRunStore; "
            "assert DurableRunner and MemoryRunStore and SQLiteRunStore"
            "; from pyagentskit.retry import ModelRetryPolicy; "
            "assert ModelRetryPolicy().max_attempts == 1"
            "; from pyagentskit.coordination import MemoryLeaseStore, SQLiteLeaseStore; "
            "from pyagentskit.postgres import PostgresLeaseStore, PostgresRunStore; "
            "assert MemoryLeaseStore and SQLiteLeaseStore; "
            "assert PostgresLeaseStore and PostgresRunStore"
            "; from pyagentskit.postgres_state import (PostgresSessionStore, "
            "PostgresMemoryStore, PostgresApprovalStore); "
            "from pyagentskit.blobs import BlobStore, S3ArtifactStore, AzureBlobArtifactStore; "
            "from pyagentskit.state_migration import migrate_sqlite_to_postgres; "
            "assert PostgresSessionStore and PostgresMemoryStore and PostgresApprovalStore; "
            "assert BlobStore and S3ArtifactStore and AzureBlobArtifactStore; "
            "assert migrate_sqlite_to_postgres"
            "; from pyagentskit.distributed import (DistributedDurableRunner, "
            "DistributedExecutionPolicy, DistributedMetricsSink, "
            "DistributedWorkerController, FencingToken, JsonLinesDistributedEventSink); "
            "assert DistributedDurableRunner and FencingToken; "
            "assert DistributedExecutionPolicy().max_renewals > 0; "
            "assert DistributedMetricsSink and DistributedWorkerController; "
            "assert JsonLinesDistributedEventSink"
        )
        run(str(python), "-c", probe, cwd=target)
        run(str(python), "-m", "pyagentskit", "--version", cwd=target)
        run(str(python), "-m", "pyagentskit", "doctor", cwd=target)
        run(str(python), "-m", "pip", "check", cwd=target)
        run(str(python), str(ROOT / "examples" / "offline_agent.py"), cwd=target)
        run(str(python), str(ROOT / "examples" / "session_agent.py"), cwd=target)
        run(str(python), str(ROOT / "examples" / "approval_agent.py"), cwd=target)
        run(str(python), str(ROOT / "examples" / "durable_agent.py"), cwd=target)
        run(str(python), str(ROOT / "examples" / "evaluate_agent.py"), cwd=target)
        run(str(python), str(ROOT / "examples" / "streaming_agent.py"), cwd=target)
        run(str(python), str(ROOT / "examples" / "parallel_tools.py"), cwd=target)
        run(str(python), str(ROOT / "examples" / "retry_agent.py"), cwd=target)
        run(str(python), str(ROOT / "examples" / "distributed_coordination.py"), cwd=target)
        run(str(python), str(ROOT / "examples" / "distributed_durable_agent.py"), cwd=target)


def main() -> None:
    verify_versions()
    verify_secret_hygiene()
    run(sys.executable, "-m", "ruff", "check", ".")
    run(sys.executable, "-m", "ruff", "format", "--check", ".")
    run(sys.executable, "-m", "mypy", "src")
    run(sys.executable, "-m", "compileall", "-q", "src")
    run(sys.executable, "-m", "pytest", "-q", "-rs")
    run(sys.executable, "scripts/benchmark_runtime.py", "--iterations", "250")
    run(sys.executable, "scripts/benchmark_streaming.py", "--iterations", "250")
    run(sys.executable, "scripts/benchmark_retry.py", "--iterations", "250")
    run(sys.executable, "scripts/benchmark_coordination.py", "--iterations", "250")
    run(sys.executable, "scripts/benchmark_distributed_operations.py", "--iterations", "250")
    wheel, sdist = build_distributions()
    run(sys.executable, "-m", "twine", "check", str(wheel), str(sdist))
    verify_archives(wheel, sdist)
    verify_reproducible_build(wheel, sdist)
    smoke_install(wheel)
    print(f"PASS: PyAgentsKit {EXPECTED_VERSION} release-check", flush=True)


if __name__ == "__main__":
    main()
