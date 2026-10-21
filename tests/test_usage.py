from __future__ import annotations

import unittest
from decimal import Decimal

from pyagentskit import Usage


class UsageTests(unittest.TestCase):
    def test_total_tokens_does_not_double_count_categories(self) -> None:
        usage = Usage(
            input_tokens=10,
            output_tokens=5,
            cached_input_tokens=4,
            reasoning_tokens=2,
        )

        self.assertEqual(usage.total_tokens, 15)

    def test_adds_usage_and_partial_cost(self) -> None:
        total = Usage(input_tokens=10) + Usage(
            output_tokens=5,
            estimated_cost_usd=Decimal("0.02"),
        )

        self.assertEqual(total.total_tokens, 15)
        self.assertEqual(total.estimated_cost_usd, Decimal("0.02"))


if __name__ == "__main__":
    unittest.main()
