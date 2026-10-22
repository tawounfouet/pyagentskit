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
EXPECTED_VERSION = "2.0.0a4"
REQUIRED_SDIST_FILES = {
    "README.md",
    "CHANGELOG.md",
    "docs/specs/MANIFEST.md",
    "docs/planning/49_PYAGENTSKIT_V2_IMPLEMENTATION_NEXT_STEPS.md",
    "docs/planning/PYAGENTSKIT_ROADMAP.md",
    "docs/releases/V2_0_0A4_RELEASE_NOTES.md",
    "docs/releases/V2_0_0A4_QUALIFICATION_EVIDENCE.md",
    "docs/guides/V2_PERSISTENCE.md",
    "docs/specs/milestones/53_PYAGENTSKIT_MILESTONE_2_0_0A4_PERSISTENCE_V2_SPEC.md",
    "examples/v2_persistence.py",
}


def run(*command: str, cwd: Path = ROOT, pythonpath: Path | None = None) -> None:
    """Execute one release command and fail on any non-zero exit."""
    print("+", " ".join(command), flush=True)
    environment = os.environ.copy()
    environment["PIP_NO_INDEX"] = "1"
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    environment["SOURCE_DATE_EPOCH"] = "1788739200"
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    if pythonpath is not None:
        existing_pythonpath = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = os.pathsep.join(
            part for part in (str(pythonpath), existing_pythonpath) if part
        )
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
            f"import sys; sys.path.insert(0, {str(ROOT / 'src')!r}); "
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


def write_checksums(wheel: Path, sdist: Path) -> None:
    """Keep release-local and repository-root checksum manifests synchronized."""

    artifacts = (sdist, wheel)
    release_lines = [f"{digest(path)}  {path.name}" for path in artifacts]
    root_lines = [f"{digest(path)}  release-dist/{path.name}" for path in artifacts]
    (DIST / "SHA256SUMS").write_text("\n".join(release_lines) + "\n", encoding="utf-8")
    (ROOT / "SHA256SUMS").write_text("\n".join(root_lines) + "\n", encoding="utf-8")


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
            "assert JsonLinesDistributedEventSink; "
            "from pyagentskit.domain import (Effect, ReconciliationEvidence, RecoveryPlanner, "
            "Run, RunStatus); "
            "from pyagentskit.application import (EffectExecutionGate, ReconcileEffect, "
            "RuntimeRecoveryExecutor); "
            "assert Run().transition(RunStatus.RUNNING).status is RunStatus.RUNNING; "
            "assert Effect and ReconciliationEvidence and RecoveryPlanner; "
            "assert EffectExecutionGate and ReconcileEffect and RuntimeRecoveryExecutor; "
            "from pyagentskit.adapters.persistence import (SQLiteRunRepository, "
            "SQLiteUnitOfWork); "
            "from pyagentskit.contracts import UnitOfWork; "
            "assert SQLiteRunRepository and SQLiteUnitOfWork and UnitOfWork"
        )
        run(str(python), "-c", probe, cwd=target)
        run(str(python), "-m", "pyagentskit", "--version", cwd=target)
        run(str(python), "-m", "pyagentskit", "doctor", cwd=target)
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
        run(str(python), str(ROOT / "examples" / "v2_effect_recovery.py"), cwd=target)
        run(str(python), str(ROOT / "examples" / "v2_persistence.py"), cwd=target)


def main() -> None:
    verify_versions()
    verify_secret_hygiene()
    run(sys.executable, "-m", "ruff", "check", ".")
    run(sys.executable, "-m", "ruff", "format", "--check", "src", "tests", "scripts", "examples")
    run(sys.executable, "-m", "mypy", "src")
    run(sys.executable, "-m", "compileall", "-q", "src")
    run(
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "pytest_cov",
        "-q",
        "-rs",
        pythonpath=ROOT / "src",
    )
    run(sys.executable, "-m", "coverage", "report", "--fail-under=90")
    run(
        sys.executable,
        "scripts/benchmark_runtime.py",
        "--iterations",
        "250",
        pythonpath=ROOT / "src",
    )
    run(
        sys.executable,
        "scripts/benchmark_streaming.py",
        "--iterations",
        "250",
        pythonpath=ROOT / "src",
    )
    run(
        sys.executable,
        "scripts/benchmark_retry.py",
        "--iterations",
        "250",
        pythonpath=ROOT / "src",
    )
    run(
        sys.executable,
        "scripts/benchmark_coordination.py",
        "--iterations",
        "250",
        pythonpath=ROOT / "src",
    )
    run(
        sys.executable,
        "scripts/benchmark_distributed_operations.py",
        "--iterations",
        "250",
        pythonpath=ROOT / "src",
    )
    wheel, sdist = build_distributions()
    run(sys.executable, "-m", "twine", "check", str(wheel), str(sdist))
    verify_archives(wheel, sdist)
    verify_reproducible_build(wheel, sdist)
    write_checksums(wheel, sdist)
    smoke_install(wheel)
    print(f"PASS: PyAgentsKit {EXPECTED_VERSION} release-check", flush=True)


if __name__ == "__main__":
    main()
