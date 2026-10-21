from __future__ import annotations

import inspect
import unittest

import pyagentskit.distributed as distributed
from pyagentskit.distributed import (
    DistributedDurableRunner,
    DistributedExecutionPolicy,
    DistributedMetrics,
    DistributedOperationEvent,
    DistributedWorkerController,
    DistributedWorkerHealth,
    FencingToken,
)


class DistributedApiStabilityTests(unittest.TestCase):
    def test_1_6_submodule_export_manifest_is_explicit(self) -> None:
        self.assertEqual(
            tuple(distributed.__all__),
            (
                "DistributedAdmissionError",
                "DistributedDurableRunner",
                "DistributedEventSink",
                "DistributedEventType",
                "DistributedExecutionPolicy",
                "DistributedMetrics",
                "DistributedMetricsSink",
                "DistributedOperationEvent",
                "DistributedWorkerController",
                "DistributedWorkerHealth",
                "DistributedWorkerState",
                "FencedOperationStore",
                "FencingToken",
                "JsonLinesDistributedEventSink",
                "LeaseLostError",
                "LeaseRenewalLimitError",
                "MemoryDistributedEventSink",
                "OpenTelemetryDistributedEventSink",
                "fencing_token_from_context",
                "resource_id_for_run",
            ),
        )

    def test_1_5_runner_constructor_remains_source_compatible(self) -> None:
        self.assertEqual(
            tuple(inspect.signature(DistributedDurableRunner).parameters),
            ("durable_runner", "lease_store", "owner_id", "policy", "event_sinks"),
        )
        self.assertEqual(
            tuple(inspect.signature(DistributedWorkerController).parameters),
            ("runner", "max_active_runs", "readiness_probe"),
        )

    def test_operational_contract_field_order_is_frozen_for_1_6_x(self) -> None:
        self.assertEqual(
            tuple(DistributedOperationEvent.model_fields),
            (
                "type",
                "occurred_at",
                "owner_id",
                "run_id",
                "resource_id",
                "tenant_id",
                "fencing_token",
                "lease_revision",
                "active_runs",
                "reason",
            ),
        )
        self.assertEqual(
            tuple(DistributedWorkerHealth.model_fields),
            (
                "owner_id",
                "state",
                "ready",
                "active_runs",
                "max_active_runs",
                "coordination_ready",
                "reason",
            ),
        )
        self.assertEqual(
            tuple(FencingToken.model_fields),
            ("resource_id", "owner_id", "tenant_id", "value", "lease_id"),
        )

    def test_policy_and_metrics_field_order_is_stable(self) -> None:
        self.assertEqual(
            tuple(DistributedExecutionPolicy.model_fields),
            (
                "lease_ttl_seconds",
                "renewal_interval_seconds",
                "max_renewals",
                "resource_prefix",
            ),
        )
        self.assertEqual(len(DistributedMetrics.model_fields), 11)


if __name__ == "__main__":
    unittest.main()
