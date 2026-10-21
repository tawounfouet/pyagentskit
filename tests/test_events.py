from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import ValidationError

from pyagentskit import AgentEvent, EventType


class AgentEventTests(unittest.TestCase):
    def test_serializes_full_ids_and_aware_timestamp(self) -> None:
        run_id = uuid4()
        trace_id = uuid4()
        event = AgentEvent(
            event_type=EventType.RUN_STARTED,
            occurred_at=datetime.now(UTC),
            run_id=run_id,
            trace_id=trace_id,
            agent_id="support.triage",
        )

        payload = json.loads(event.model_dump_json())
        self.assertEqual(payload["run_id"], str(run_id))
        self.assertEqual(payload["trace_id"], str(trace_id))
        self.assertIn("+00:00", payload["occurred_at"].replace("Z", "+00:00"))

    def test_rejects_naive_timestamp(self) -> None:
        with self.assertRaises(ValidationError):
            AgentEvent(
                event_type=EventType.RUN_STARTED,
                occurred_at=datetime(2026, 9, 4),
                run_id=uuid4(),
                trace_id=uuid4(),
                agent_id="support.triage",
            )

    def test_rejects_unknown_fields(self) -> None:
        with self.assertRaises(ValidationError):
            AgentEvent(
                event_type=EventType.RUN_STARTED,
                occurred_at=datetime.now(UTC),
                run_id=uuid4(),
                trace_id=uuid4(),
                agent_id="support.triage",
                secret="not allowed",
            )


if __name__ == "__main__":
    unittest.main()
