from __future__ import annotations

import ast
import unittest
from pathlib import Path

from pyagentskit.domain import (
    Actor,
    ActorId,
    AggregateVersion,
    Approval,
    ApprovalScope,
    ApprovalStatus,
    Artifact,
    ArtifactChecksum,
    AuditEvent,
    Conversation,
    ConversationMessage,
    Effect,
    EffectStatus,
    ExternalReference,
    FencingToken,
    Fingerprint,
    Lease,
    LeaseStatus,
    Participant,
    ReconciliationCase,
    Run,
    RunStatus,
    RuntimeBinding,
    RuntimeCapability,
    RuntimeInvocation,
    Session,
    Worker,
    WorkerId,
    WorkerStatus,
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

    def test_shared_kernel_values_validate_and_compare(self) -> None:
        self.assertEqual(ActorId("actor-1").value, "actor-1")
        self.assertEqual(AggregateVersion(1).next().value, 2)
        self.assertEqual(Fingerprint.from_text("same"), Fingerprint.from_text("same"))
        self.assertEqual(ExternalReference("github", "issue-1").key, "issue-1")
        self.assertEqual(ArtifactChecksum("sha256", "abc").algorithm, "sha256")

        with self.assertRaises(ValueError):
            ActorId("")
        with self.assertRaises(ValueError):
            AggregateVersion(-1)
        with self.assertRaises(ValueError):
            FencingToken(-1)
        with self.assertRaises(ValueError):
            Fingerprint("not-a-digest")
        with self.assertRaises(ValueError):
            ExternalReference("", "key")
        with self.assertRaises(ValueError):
            ArtifactChecksum("", "value")

    def test_domain_entities_keep_semantic_boundaries(self) -> None:
        actor = Actor(kind="human", label="Thomas")
        participant = Participant(actor_id=actor.id, role="requester")
        worker = Worker().transition(WorkerStatus.READY).transition(WorkerStatus.DRAINING)
        session = Session()
        message = ConversationMessage(actor=str(actor.id), content="hello")
        conversation = Conversation(session_id=session.id).append(message)
        binding = RuntimeBinding(
            runtime_name="native",
            capabilities=frozenset({RuntimeCapability.INVOKE}),
        )
        invocation = RuntimeInvocation(
            run_id=Run().id,
            binding_id=binding.id,
            input="run",
        )
        artifact = Artifact(
            name="report.json",
            checksum=ArtifactChecksum("sha256", "abc"),
            external_reference=ExternalReference("store", "report-1"),
        )
        audit = AuditEvent(event_type="run.started", subject=str(invocation.id))
        reconciliation = ReconciliationCase(effect_id=Effect().id, reason="ambiguous")

        self.assertEqual(participant.actor_id, actor.id)
        self.assertEqual(worker.status, WorkerStatus.DRAINING)
        self.assertEqual(len(conversation.messages), 1)
        self.assertEqual(invocation.binding_id, binding.id)
        self.assertEqual(artifact.name, "report.json")
        self.assertEqual(audit.event_type, "run.started")
        self.assertTrue(reconciliation.resolve("confirmed").resolved)

    def test_entity_construction_rejects_missing_required_values(self) -> None:
        with self.assertRaises(ValueError):
            Actor(kind="human")
        with self.assertRaises(ValueError):
            Participant()
        with self.assertRaises(ValueError):
            Lease()
        with self.assertRaises(ValueError):
            ConversationMessage(actor="human")
        with self.assertRaises(ValueError):
            RuntimeBinding()
        with self.assertRaises(ValueError):
            RuntimeInvocation()
        with self.assertRaises(ValueError):
            Artifact()
        with self.assertRaises(ValueError):
            AuditEvent(subject="run")
        with self.assertRaises(ValueError):
            ReconciliationCase()

    def test_worker_and_reconciliation_terminality(self) -> None:
        stopped = Worker().transition(WorkerStatus.STOPPED)
        with self.assertRaises(InvalidTransitionError):
            stopped.transition(WorkerStatus.READY)

        case = ReconciliationCase(reason="unknown outcome").resolve("manual review")
        with self.assertRaises(InvalidTransitionError):
            case.resolve("second resolution")
        with self.assertRaises(ValueError):
            ReconciliationCase(reason="unknown outcome").resolve("")

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
