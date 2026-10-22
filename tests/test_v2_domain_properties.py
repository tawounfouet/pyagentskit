from __future__ import annotations

import unittest

from hypothesis import assume, given
from hypothesis import strategies as st

from pyagentskit.domain import (
    AggregateVersion,
    Approval,
    ApprovalStatus,
    Effect,
    EffectStatus,
    FencingToken,
    IdempotencyKey,
    InputFingerprint,
    Lease,
    Run,
    RunStatus,
    WorkerId,
)
from pyagentskit.domain.errors import (
    IdempotencyConflictError,
    InvalidTransitionError,
    StaleFencingTokenError,
)


class V2DomainPropertyTests(unittest.TestCase):
    @given(
        terminal=st.sampled_from((RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED)),
        target=st.sampled_from(tuple(RunStatus)),
    )
    def test_terminal_runs_never_transition(self, terminal: RunStatus, target: RunStatus) -> None:
        run = Run().transition(RunStatus.RUNNING).transition(terminal)

        with self.assertRaises(InvalidTransitionError):
            run.transition(target)

    @given(
        terminal=st.sampled_from(
            (
                ApprovalStatus.APPROVED,
                ApprovalStatus.REJECTED,
                ApprovalStatus.EXPIRED,
                ApprovalStatus.CANCELLED,
            )
        ),
        target=st.sampled_from(tuple(ApprovalStatus)),
    )
    def test_terminal_approvals_never_transition(
        self,
        terminal: ApprovalStatus,
        target: ApprovalStatus,
    ) -> None:
        approval = Approval(subject="effect-1").transition(terminal)

        with self.assertRaises(InvalidTransitionError):
            approval.transition(target)

    @given(
        terminal=st.sampled_from((EffectStatus.SUCCEEDED, EffectStatus.FAILED)),
        target=st.sampled_from(tuple(EffectStatus)),
    )
    def test_terminal_effects_never_replay(
        self,
        terminal: EffectStatus,
        target: EffectStatus,
    ) -> None:
        effect = Effect().begin().transition(terminal)

        with self.assertRaises(InvalidTransitionError):
            effect.transition(target)

    @given(
        first=st.text(min_size=1, max_size=64),
        second=st.text(min_size=1, max_size=64),
    )
    def test_same_idempotency_key_never_accepts_different_fingerprint(
        self,
        first: str,
        second: str,
    ) -> None:
        assume(first != second)
        key = IdempotencyKey("property", "same-effect")
        effect = Effect(
            idempotency_key=key,
            fingerprint=InputFingerprint.from_text(first),
        )

        with self.assertRaises(IdempotencyConflictError):
            effect.assert_same_intent(key, InputFingerprint.from_text(second))

    @given(value=st.integers(min_value=0, max_value=2**31 - 2))
    def test_aggregate_versions_are_strictly_monotonic(self, value: int) -> None:
        version = AggregateVersion(value)

        self.assertEqual(version.next().value, value + 1)
        self.assertGreater(version.next(), version)

    @given(
        current=st.integers(min_value=0, max_value=2**31 - 1),
        candidate=st.integers(min_value=0, max_value=2**31 - 1),
    )
    def test_fencing_rejects_non_increasing_tokens(self, current: int, candidate: int) -> None:
        lease = Lease(resource="run-1")
        worker = WorkerId("worker-1")
        held = lease.acquire(worker, FencingToken(current + 1))
        released = held.release()

        if candidate <= current + 1:
            with self.assertRaises(StaleFencingTokenError):
                released.acquire(worker, FencingToken(candidate))
        else:
            reacquired = released.acquire(worker, FencingToken(candidate))
            self.assertEqual(reacquired.fencing_token, FencingToken(candidate))


if __name__ == "__main__":
    unittest.main()
