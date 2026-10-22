from __future__ import annotations

import ast
import unittest
from pathlib import Path

from pyagentskit.domain import (
    Approval,
    ApprovalScope,
    ApprovalStatus,
    Effect,
    EffectStatus,
    FencingToken,
    Lease,
    LeaseStatus,
    Run,
    RunStatus,
    WorkerId,
)
from pyagentskit.domain.errors import (
    InvalidTransitionError,
    StaleFencingTokenError,
)


class V2DomainFoundationTests(unittest.TestCase):
    def test_run_state_machine_preserves_terminality(self) -> None:
        run = Run().transition(RunStatus.RUNNING).transition(RunStatus.WAITING)
        resumed = run.transition(RunStatus.RUNNING).transition(RunStatus.SUCCEEDED)

        self.assertEqual(resumed.status, RunStatus.SUCCEEDED)
        self.assertEqual(resumed.version.value, 4)
        with self.assertRaises(InvalidTransitionError):
            resumed.transition(RunStatus.RUNNING)

    def test_effect_cannot_be_replayed_after_success(self) -> None:
        effect = Effect().transition(EffectStatus.STARTED).transition(EffectStatus.SUCCEEDED)

        with self.assertRaises(InvalidTransitionError):
            effect.transition(EffectStatus.STARTED)

    def test_approval_scope_is_immutable_and_terminal(self) -> None:
        approval = Approval(scope=ApprovalScope.EFFECT, subject="effect-1")
        approved = approval.transition(ApprovalStatus.APPROVED)

        self.assertEqual(approved.scope, ApprovalScope.EFFECT)
        with self.assertRaises(InvalidTransitionError):
            approved.transition(ApprovalStatus.REJECTED)

    def test_lease_requires_a_strictly_new_fencing_token(self) -> None:
        lease = Lease(resource="run-1")
        worker = WorkerId("worker-1")
        held = lease.acquire(worker, FencingToken(1))

        self.assertEqual(held.status, LeaseStatus.HELD)
        with self.assertRaises(StaleFencingTokenError):
            held.release().acquire(worker, FencingToken(1))

    def test_domain_does_not_import_infrastructure_layers(self) -> None:
        root = Path(__file__).parents[1] / "src" / "pyagentskit" / "domain"
        forbidden = {"pyagentskit.adapters", "pyagentskit.api", "pyagentskit.compat"}

        for path in root.glob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported = {alias.name for alias in node.names}
                elif isinstance(node, ast.ImportFrom):
                    imported = {node.module or ""}
                else:
                    continue
                self.assertTrue(forbidden.isdisjoint(imported), path)
