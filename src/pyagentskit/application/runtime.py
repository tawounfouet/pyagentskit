"""Runtime application ports, registry and deterministic negotiation."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..domain import (
    NormalizedRuntimeEvent,
    RejectedCandidate,
    RejectionReason,
    RuntimeBinding,
    RuntimeCancelRequest,
    RuntimeCancelResult,
    RuntimeCapability,
    RuntimeCheckpoint,
    RuntimeDescriptor,
    RuntimeHandle,
    RuntimeRequirements,
    RuntimeResumeRequest,
    RuntimeSelectionPolicy,
    RuntimeStartRequest,
    RuntimeStatus,
)
from ..domain.errors import (
    CapabilityNegotiationError,
    RuntimeBindingError,
    RuntimeRegistrationError,
)


@runtime_checkable
class AgentRuntimeAdapter(Protocol):
    """Provider-neutral port implemented by every agent runtime adapter."""

    @property
    def descriptor(self) -> RuntimeDescriptor:
        """Return a side-effect-free capability declaration."""
        ...

    async def start(self, request: RuntimeStartRequest) -> RuntimeHandle:
        """Start one runtime invocation."""
        ...

    async def resume(self, request: RuntimeResumeRequest) -> RuntimeHandle:
        """Resume one invocation when the descriptor declares ``RESUME``."""
        ...

    async def cancel(self, request: RuntimeCancelRequest) -> RuntimeCancelResult:
        """Request cancellation without implying effect rollback."""
        ...

    async def inspect(self, handle: RuntimeHandle) -> RuntimeStatus:
        """Return the normalized status for one opaque handle."""
        ...

    def events(self, handle: RuntimeHandle) -> AsyncIterator[NormalizedRuntimeEvent]:
        """Stream normalized runtime events."""
        ...

    async def checkpoint(self, handle: RuntimeHandle) -> RuntimeCheckpoint | None:
        """Return a native checkpoint when supported."""
        ...

    async def close(self) -> None:
        """Release adapter-owned resources."""
        ...


@dataclass(frozen=True, slots=True)
class RuntimeCandidate:
    """A descriptor together with the adapter that implements it."""

    descriptor: RuntimeDescriptor
    adapter: AgentRuntimeAdapter


@dataclass(frozen=True, slots=True)
class NegotiationResult:
    """Explainable result of capability negotiation."""

    selected: RuntimeCandidate | None
    matched_required_capabilities: frozenset[RuntimeCapability]
    missing_preferred_capabilities: frozenset[RuntimeCapability]
    rejected: tuple[RejectedCandidate, ...]
    reason: str
    policy_version: str

    @property
    def selected_runtime_id(self) -> str | None:
        return None if self.selected is None else self.selected.descriptor.runtime_id

    @property
    def selected_capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset() if self.selected is None else self.selected.descriptor.capabilities


def _version_matches(required: str | None, offered: str | None) -> bool:
    return required is None or required == offered


class CapabilityNegotiator:
    """Select the safest compatible candidate with stable tie-breaking."""

    def negotiate(
        self,
        requirements: RuntimeRequirements,
        candidates: Sequence[RuntimeCandidate],
        policy: RuntimeSelectionPolicy | None = None,
    ) -> NegotiationResult:
        selection_policy = policy or RuntimeSelectionPolicy()
        compatible: list[RuntimeCandidate] = []
        rejected: list[RejectedCandidate] = []

        for candidate in candidates:
            reasons = self._rejection_reasons(requirements, candidate.descriptor)
            if reasons:
                rejected.append(RejectedCandidate(candidate.descriptor.runtime_id, tuple(reasons)))
            else:
                compatible.append(candidate)

        if not compatible:
            raise CapabilityNegotiationError(self._failure_message(requirements, rejected))

        def score(candidate: RuntimeCandidate) -> tuple[int, int, int, int]:
            descriptor = candidate.descriptor
            preferred_index = (
                len(selection_policy.preferred_runtime_ids)
                - selection_policy.preferred_runtime_ids.index(descriptor.runtime_id)
                if descriptor.runtime_id in selection_policy.preferred_runtime_ids
                else 0
            )
            preferred_matches = len(descriptor.capabilities & requirements.preferred_capabilities)
            return (
                descriptor.side_effect_control_level if selection_policy.prefer_full_control else 0,
                preferred_matches,
                descriptor.qualification_level
                if selection_policy.prefer_highest_qualification
                else 0,
                preferred_index,
            )

        selected = sorted(
            compatible,
            key=lambda candidate: (
                *(-value for value in score(candidate)),
                candidate.descriptor.runtime_id,
            ),
        )[0]
        missing_preferred = requirements.preferred_capabilities - selected.descriptor.capabilities
        matched_required = requirements.required_capabilities & selected.descriptor.capabilities
        return NegotiationResult(
            selected=selected,
            matched_required_capabilities=frozenset(matched_required),
            missing_preferred_capabilities=frozenset(missing_preferred),
            rejected=tuple(sorted(rejected, key=lambda item: item.runtime_id)),
            reason=(
                f"selected {selected.descriptor.runtime_id}: required capabilities satisfied; "
                f"control={selected.descriptor.side_effect_control_level.name}; "
                f"qualification={selected.descriptor.qualification_level.name}"
            ),
            policy_version=selection_policy.policy_version,
        )

    @staticmethod
    def _rejection_reasons(
        requirements: RuntimeRequirements, descriptor: RuntimeDescriptor
    ) -> list[RejectionReason]:
        reasons: list[RejectionReason] = []
        if requirements.runtime_id is not None and descriptor.runtime_id != requirements.runtime_id:
            reasons.append(RejectionReason.RUNTIME_NOT_FOUND)
        if (
            requirements.runtime_family is not None
            and descriptor.runtime_family != requirements.runtime_family
        ):
            reasons.append(RejectionReason.RUNTIME_FAMILY_MISMATCH)
        if requirements.required_capabilities - descriptor.capabilities:
            reasons.append(RejectionReason.MISSING_REQUIRED_CAPABILITY)
        if requirements.forbidden_capabilities & descriptor.capabilities:
            reasons.append(RejectionReason.FORBIDDEN_CAPABILITY)
        if descriptor.qualification_level < requirements.minimum_qualification_level:
            reasons.append(RejectionReason.QUALIFICATION_TOO_LOW)
        if descriptor.side_effect_control_level < requirements.minimum_side_effect_control:
            reasons.append(RejectionReason.SIDE_EFFECT_CONTROL_TOO_WEAK)
        if not _version_matches(requirements.runtime_version, descriptor.runtime_version):
            reasons.append(RejectionReason.VERSION_INCOMPATIBLE)
        if (
            requirements.platform is not None
            and requirements.platform not in descriptor.supported_platforms
        ):
            reasons.append(RejectionReason.PLATFORM_INCOMPATIBLE)
        return reasons

    @staticmethod
    def _failure_message(
        requirements: RuntimeRequirements, rejected: Sequence[RejectedCandidate]
    ) -> str:
        details = "; ".join(
            f"{candidate.runtime_id}: {','.join(reason.value for reason in candidate.reasons)}"
            for candidate in rejected
        )
        requested = requirements.runtime_id or requirements.runtime_family or "any runtime"
        return f"no runtime satisfies {requested}: {details or 'registry is empty'}"


class RuntimeBindingPolicy:
    """Protect the durable runtime family chosen for one Run."""

    @staticmethod
    def validate_candidate(current: RuntimeBinding, candidate: RuntimeDescriptor) -> None:
        """Reject silent runtime-family changes for an existing binding."""

        if current.runtime_family is None:
            raise RuntimeBindingError(
                "runtime binding has no family snapshot; rebinding cannot be validated safely"
            )
        if candidate.runtime_family != current.runtime_family:
            raise RuntimeBindingError(
                "runtime family cannot change silently: "
                f"{current.runtime_family!r} -> {candidate.runtime_family!r}"
            )


@runtime_checkable
class RuntimeRegistry(Protocol):
    """Process-local registry of known runtime adapters."""

    def register(self, adapter: AgentRuntimeAdapter) -> None: ...

    def unregister(self, runtime_id: str) -> AgentRuntimeAdapter: ...

    def get(self, runtime_id: str) -> AgentRuntimeAdapter: ...

    def list(self) -> Sequence[RuntimeDescriptor]: ...

    def find(self, requirements: RuntimeRequirements) -> Sequence[RuntimeCandidate]: ...


class InMemoryRuntimeRegistry:
    """Deterministic process-local registry used by the composition root."""

    def __init__(self, negotiator: CapabilityNegotiator | None = None) -> None:
        self._adapters: dict[str, RuntimeCandidate] = {}
        self.negotiator = negotiator or CapabilityNegotiator()

    def register(self, adapter: AgentRuntimeAdapter) -> None:
        try:
            descriptor = adapter.descriptor
        except AttributeError as exc:
            raise RuntimeRegistrationError("runtime adapter must expose descriptor") from exc
        if not isinstance(descriptor, RuntimeDescriptor):
            raise RuntimeRegistrationError("runtime descriptor has an invalid type")
        if descriptor.runtime_id in self._adapters:
            raise RuntimeRegistrationError(
                f"runtime id is already registered: {descriptor.runtime_id}"
            )
        self._adapters[descriptor.runtime_id] = RuntimeCandidate(descriptor, adapter)

    def unregister(self, runtime_id: str) -> AgentRuntimeAdapter:
        try:
            return self._adapters.pop(runtime_id).adapter
        except KeyError as exc:
            raise RuntimeRegistrationError(f"runtime id is not registered: {runtime_id}") from exc

    def get(self, runtime_id: str) -> AgentRuntimeAdapter:
        try:
            return self._adapters[runtime_id].adapter
        except KeyError as exc:
            raise RuntimeRegistrationError(f"runtime id is not registered: {runtime_id}") from exc

    def list(self) -> Sequence[RuntimeDescriptor]:
        return tuple(
            candidate.descriptor
            for candidate in sorted(
                self._adapters.values(), key=lambda item: item.descriptor.runtime_id
            )
        )

    def find(self, requirements: RuntimeRequirements) -> Sequence[RuntimeCandidate]:
        candidates = tuple(self._adapters.values())
        return tuple(
            candidate
            for candidate in candidates
            if not CapabilityNegotiator._rejection_reasons(requirements, candidate.descriptor)
        )

    def negotiate(
        self,
        requirements: RuntimeRequirements,
        policy: RuntimeSelectionPolicy | None = None,
    ) -> NegotiationResult:
        return self.negotiator.negotiate(requirements, tuple(self._adapters.values()), policy)
