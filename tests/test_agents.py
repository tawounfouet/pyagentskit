from __future__ import annotations

import unittest

from pydantic import ValidationError

from pyagentskit import AgentDefinition, ModelRef, RunLimits


class AgentDefinitionTests(unittest.TestCase):
    def test_builds_serializable_definition(self) -> None:
        definition = AgentDefinition(
            id="support.triage",
            version="1.0.0",
            instructions="Classify the request.",
            model=ModelRef(provider="openai", name="gpt-5"),
            tools=("customer.get",),
            limits=RunLimits(max_steps=4),
        )

        self.assertEqual(definition.model.qualified_name, "openai:gpt-5")
        self.assertEqual(definition.tools, ("customer.get",))
        self.assertEqual(definition.limits.max_steps, 4)

    def test_rejects_duplicate_tools(self) -> None:
        with self.assertRaises(ValidationError):
            AgentDefinition(
                id="support.triage",
                version="1.0.0",
                instructions="Classify the request.",
                model=ModelRef(provider="openai", name="gpt-5"),
                tools=("customer.get", "customer.get"),
            )

    def test_rejects_invalid_identifier_and_version(self) -> None:
        with self.assertRaises(ValidationError):
            AgentDefinition(
                id="Support Triage",
                version="v1",
                instructions="Classify the request.",
                model=ModelRef(provider="openai", name="gpt-5"),
            )


if __name__ == "__main__":
    unittest.main()
