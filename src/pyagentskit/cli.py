"""Dependency-free CLI facade over PyAgentsKit public contracts."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from ._version import __version__
from .agents import AgentDefinition
from .diagnostics import run_doctor
from .durability import SQLiteRunStore
from .evals import EvalDataset, compare_reports, load_eval_report
from .exceptions import PyAgentsKitError
from .messages import TextContent
from .models import FinishReason, ModelResponse
from .runtime import Runner
from .state_migration import migrate_sqlite_to_postgres
from .testing import FakeModel


def _print(value: Any) -> None:
    if hasattr(value, "model_dump_json"):
        print(value.model_dump_json(indent=2))
    else:
        print(json.dumps(value, indent=2, default=str))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyagentskit")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Inspect the local installation")

    run = commands.add_parser("run", help="Run one safe offline smoke scenario")
    run.add_argument("agent", type=Path)
    run.add_argument("--input", required=True)
    run.add_argument("--response", required=True)

    config = commands.add_parser("config", help="Validate configuration")
    config_commands = config.add_subparsers(dest="config_command", required=True)
    validate = config_commands.add_parser("validate")
    validate.add_argument("path", type=Path)

    evaluations = commands.add_parser("eval", help="Validate or compare eval artifacts")
    eval_commands = evaluations.add_subparsers(dest="eval_command", required=True)
    eval_validate = eval_commands.add_parser("validate")
    eval_validate.add_argument("path", type=Path)
    compare = eval_commands.add_parser("compare")
    compare.add_argument("baseline", type=Path)
    compare.add_argument("candidate", type=Path)
    compare.add_argument("--max-pass-rate-regression", type=float, default=0.0)

    checkpoint = commands.add_parser("checkpoint", help="Inspect durable state")
    checkpoint_commands = checkpoint.add_subparsers(dest="checkpoint_command", required=True)
    inspect = checkpoint_commands.add_parser("inspect")
    inspect.add_argument("database", type=Path)
    inspect.add_argument("run_id", type=UUID)
    inspect.add_argument("--tenant")

    migration = commands.add_parser("migrate-state", help="Migrate SQLite state to PostgreSQL")
    migration.add_argument("--sqlite", type=Path, action="append", required=True)
    migration.add_argument(
        "--postgres-dsn-env",
        default="PYAGENTSKIT_POSTGRES_DSN",
        help="Environment variable containing the PostgreSQL DSN",
    )
    migration.add_argument("--table-prefix", default="pyagentskit")
    migration.add_argument("--dry-run", action="store_true")
    migration.add_argument("--overwrite", action="store_true")
    return parser


async def _inspect_checkpoint(arguments: argparse.Namespace) -> dict[str, Any]:
    store = SQLiteRunStore(arguments.database)
    try:
        checkpoints = await store.list_checkpoints(arguments.run_id, tenant_id=arguments.tenant)
        effects = await store.list_effects(arguments.run_id, tenant_id=arguments.tenant)
        return {
            "checkpoints": [item.model_dump(mode="json") for item in checkpoints],
            "effects": [item.model_dump(mode="json") for item in effects],
        }
    finally:
        store.close()


async def _run_offline(arguments: argparse.Namespace) -> Any:
    definition = AgentDefinition.model_validate_json(arguments.agent.read_text(encoding="utf-8"))
    if definition.tools:
        raise ValueError("Offline CLI runs do not load application tools")
    response = ModelResponse(
        id="cli-offline-response",
        model=definition.model.name,
        content=(TextContent(text=arguments.response),),
        finish_reason=FinishReason.STOP,
    )
    return await Runner(FakeModel((response,))).run(definition, arguments.input)


async def _migrate_state(arguments: argparse.Namespace) -> Any:
    from .postgres import create_asyncpg_pool

    if arguments.dry_run:
        return await migrate_sqlite_to_postgres(
            arguments.sqlite,
            None,
            table_prefix=arguments.table_prefix,
            dry_run=True,
            overwrite=arguments.overwrite,
        )
    dsn = os.getenv(arguments.postgres_dsn_env)
    if not dsn:
        raise ValueError(
            f"PostgreSQL DSN environment variable is missing: {arguments.postgres_dsn_env}"
        )
    pool = await create_asyncpg_pool(dsn)
    try:
        return await migrate_sqlite_to_postgres(
            arguments.sqlite,
            pool,
            table_prefix=arguments.table_prefix,
            overwrite=arguments.overwrite,
        )
    finally:
        close = getattr(pool, "close", None)
        if close is not None:
            await close()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process-compatible status code."""

    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "doctor":
            report = run_doctor()
            _print(report)
            return 0 if report.healthy else 1
        if arguments.command == "run":
            _print(asyncio.run(_run_offline(arguments)))
            return 0
        if arguments.command == "config":
            document = arguments.path.read_text(encoding="utf-8")
            _print(AgentDefinition.model_validate_json(document))
            return 0
        if arguments.command == "eval" and arguments.eval_command == "validate":
            document = arguments.path.read_text(encoding="utf-8")
            _print(EvalDataset.model_validate_json(document))
            return 0
        if arguments.command == "eval":
            comparison = compare_reports(
                load_eval_report(arguments.baseline),
                load_eval_report(arguments.candidate),
                max_pass_rate_regression=arguments.max_pass_rate_regression,
            )
            _print(comparison)
            return 0 if comparison.acceptable else 2
        if arguments.command == "checkpoint":
            _print(asyncio.run(_inspect_checkpoint(arguments)))
            return 0
        if arguments.command == "migrate-state":
            _print(asyncio.run(_migrate_state(arguments)))
            return 0
    except (OSError, PyAgentsKitError, ValueError, ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
