from __future__ import annotations

import unittest

from pydantic import ValidationError

from pyagentskit import ToolDefinition, ToolRisk


class ToolDefinitionTests(unittest.TestCase):
    def test_read_tool_has_governance_metadata(self) -> None:
        definition = ToolDefinition(
            name="customer.get",
            description="Retrieve a customer.",
            input_schema={"type": "object"},
            risk=ToolRisk.READ,
            idempotent=True,
            tags=("customer", "read"),
        )

        self.assertTrue(definition.idempotent)
        self.assertEqual(definition.risk, ToolRisk.READ)

    def test_destructive_tool_requires_approval(self) -> None:
        with self.assertRaises(ValidationError):
            ToolDefinition(
                name="customer.delete",
                description="Delete a customer.",
                input_schema={"type": "object"},
                risk=ToolRisk.DESTRUCTIVE,
            )

    def test_code_execution_requires_approval(self) -> None:
        with self.assertRaises(ValidationError):
            ToolDefinition(
                name="code.execute",
                description="Execute arbitrary code.",
                input_schema={"type": "object"},
                risk=ToolRisk.CODE_EXECUTION,
            )

    def test_tags_must_be_unique(self) -> None:
        with self.assertRaises(ValidationError):
            ToolDefinition(
                name="customer.get",
                description="Retrieve a customer.",
                input_schema={"type": "object"},
                tags=("customer", "customer"),
            )


if __name__ == "__main__":
    unittest.main()
