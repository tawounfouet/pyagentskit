from __future__ import annotations

import unittest

import pyagentskit


class PublicApiTests(unittest.TestCase):
    def test_version_matches_phase_release(self) -> None:
        self.assertEqual(pyagentskit.__version__, "2.0.0a2")

    def test_public_exports_are_unique(self) -> None:
        self.assertEqual(len(pyagentskit.__all__), len(set(pyagentskit.__all__)))


if __name__ == "__main__":
    unittest.main()
